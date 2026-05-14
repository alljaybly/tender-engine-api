"""
Tender document processing pipeline.

Stages:
  1. File validation & metadata extraction
  2. Document text extraction (PDF/DOCX/TXT)
  3. Entity extraction (sector, duration, location, workforce, schedule)
  4. BOQ extraction (uses boq_extractor.py)
  5. Pricing engine integration (builds PricingInput, runs calculate)
  6. Final result assembly

Runs asynchronously in a background task.  Updates job progress in
the database at each stage.  Tracks per-stage ProcessingEvents.
Supports partial_success status when some stages fail but core
functionality remains usable.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..schemas.process import ProcessingResult, ExtractedBOQItem
from ..services.database import get_db, close_db

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "v1"

# Configurable timeouts (seconds)
PDF_EXTRACTION_TIMEOUT = 120
BOQ_EXTRACTION_TIMEOUT = 180

# Valid pipeline stages for event logging
STAGES = [
    "upload_received",
    "metadata_extraction",
    "text_extraction",
    "entity_extraction",
    "boq_analysis",
    "pricing_calculation",
    "finalisation",
]

# ── Timeout helper ─────────────────────────────────────────────────


async def _run_with_timeout(coro, timeout: int, label: str):
    """Run an async coroutine with a timeout.  Returns (result, timed_out)."""
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return result, False
    except asyncio.TimeoutError:
        logger.warning("[PIPELINE] Timeout in stage '%s' after %ds", label, timeout)
        return None, True


# ── Processing event helpers ───────────────────────────────────────


async def _log_event(tender_id: str, stage: str, status: str,
                     details: Optional[str] = None,
                     duration_ms: Optional[int] = None) -> None:
    """Insert a ProcessingEvent record."""
    try:
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO processing_events
                   (tender_id, stage, status, details, duration_ms)
                   VALUES (?, ?, ?, ?, ?)""",
                (tender_id, stage, status, details, duration_ms),
            )
            await db.commit()
        finally:
            await close_db(db)
    except Exception as e:
        logger.warning("[PIPELINE] Failed to log event: %s", e)


async def _record_stage(tender_id: str, stage: str, success: bool,
                        details: Optional[str] = None,
                        start_time: Optional[float] = None) -> None:
    """Convenience: log a stage event with optional timing."""
    duration = None
    if start_time is not None:
        duration = int((time.monotonic() - start_time) * 1000)
    status = "success" if success else "failed"
    await _log_event(tender_id, stage, status, details, duration)


# ── Stage 1: Metadata ──────────────────────────────────────────────


def _extract_metadata(file_path: str, original_name: str) -> Dict[str, Any]:
    """Basic file metadata: size, type, extension."""
    meta: Dict[str, Any] = {}
    try:
        stat = os.stat(file_path)
        meta["size_bytes"] = stat.st_size
    except OSError:
        meta["size_bytes"] = 0

    ext = os.path.splitext(original_name)[1].lower()
    meta["file_type"] = ext.lstrip(".") if ext else "unknown"

    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                meta["page_count"] = len(pdf.pages)
        except Exception as e:
            logger.warning("[PIPELINE] Could not count PDF pages: %s", e)
            meta["page_count"] = 0

    return meta


# ── Stage 2: Text extraction ───────────────────────────────────────


async def _extract_text(file_path: str, original_name: str) -> Optional[str]:
    """
    Extract full text from the uploaded document.
    Supports PDF, DOCX, and TXT with timeout protection.
    """
    ext = os.path.splitext(original_name)[1].lower()

    if ext == ".pdf":
        def _extract_pdf() -> Optional[str]:
            import pdfplumber
            try:
                # pdfplumber.open() will raise an exception for malformed PDFs
                text_parts: List[str] = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text_parts.append(t)
                return "\n".join(text_parts) if text_parts else None
            except Exception as e:
                logger.warning("[PIPELINE] PDF extraction inner error: %s", e)
                raise  # re-raise so the outer handler catches it

        loop = asyncio.get_event_loop()
        try:
            full_text = await asyncio.wait_for(
                loop.run_in_executor(None, _extract_pdf),
                timeout=PDF_EXTRACTION_TIMEOUT,
            )
            if full_text:
                logger.info("[PIPELINE] Extracted %d chars from PDF", len(full_text))
            return full_text
        except asyncio.TimeoutError:
            logger.warning("[PIPELINE] PDF extraction timed out after %ds",
                           PDF_EXTRACTION_TIMEOUT)
            return None
        except Exception as e:
            logger.warning("[PIPELINE] PDF text extraction failed gracefully: %s", e)
            return None

    elif ext == ".docx":
        try:
            from docx import Document
            doc = Document(file_path)
            text_parts = [p.text for p in doc.paragraphs]
            full_text = "\n".join(text_parts)
            logger.info("[PIPELINE] Extracted %d chars from DOCX", len(full_text))
            return full_text
        except Exception as e:
            logger.warning("[PIPELINE] DOCX text extraction failed: %s", e)
            return None

    elif ext == ".txt":
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                full_text = f.read()
            logger.info("[PIPELINE] Read %d chars from TXT", len(full_text))
            return full_text
        except Exception as e:
            logger.warning("[PIPELINE] TXT text extraction failed: %s", e)
            return None

    else:
        logger.warning("[PIPELINE] Unsupported file type: %s", ext)
        return None


# ── Stage 3: Entity extraction ─────────────────────────────────────


def _extract_entities(text: str) -> Dict[str, Any]:
    """Run all heuristic extractors on the extracted text."""
    from .extractors.sector_detector import detect_sector
    from .extractors.duration_extractor import detect_duration
    from .extractors.location_extractor import detect_locations
    from .extractors.workforce_extractor import detect_workforce
    from .extractors.schedule_extractor import detect_schedule

    entities: Dict[str, Any] = {}
    entities["detected_sector"] = detect_sector(text)
    entities["sector_confidence"] = "High" if entities["detected_sector"] else "None"
    entities["detected_duration_months"] = detect_duration(text)
    entities["detected_locations"] = detect_locations(text)
    entities["detected_workforce"] = detect_workforce(text)
    entities["detected_schedule"] = detect_schedule(text)
    return entities


# ── Stage 4: BOQ extraction ────────────────────────────────────────


async def _extract_boq(file_path: str) -> Tuple[List[Dict[str, Any]], Optional[str], List[str]]:
    """
    Run the existing BOQ extractor with timeout protection.
    Returns (items, confidence, warnings).
    """
    from .boq_extractor import extract_from_pdf

    def _run_boq():
        return extract_from_pdf(file_path)

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_boq),
            timeout=BOQ_EXTRACTION_TIMEOUT,
        )
        items: List[Dict[str, Any]] = []
        for boq_item in result.items:
            items.append({
                "item_no": boq_item.item_no,
                "description": boq_item.description,
                "quantity": boq_item.quantity,
                "unit": boq_item.unit,
                "rate": boq_item.rate,
                "amount": boq_item.amount,
            })
        return items, result.confidence, result.warnings
    except asyncio.TimeoutError:
        logger.warning("[PIPELINE] BOQ extraction timed out after %ds",
                       BOQ_EXTRACTION_TIMEOUT)
        return [], None, ["BOQ extraction timed out"]
    except Exception as e:
        logger.warning("[PIPELINE] BOQ extraction failed: %s", e)
        return [], None, [f"BOQ extraction failed: {e}"]


# ── Stage 5: Pricing integration ───────────────────────────────────


def _run_pricing(
    entities: Dict[str, Any],
    boq_items: List[Dict[str, Any]],
    boq_confidence: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], str, Optional[str]]:
    """
    Run pricing via the PricingEngine adapter.

    Returns (pricing_result_dict, pricing_mode, pricing_unavailable_reason).

    pricing_mode is:
      - "boq_based" when BOQ items exist and confidence >= Medium
      - "estimated" when no BOQ or low confidence

    pricing_unavailable_reason is set when pricing fails, else None.

    The adapter properly calls PricingEngine.calculate(tender_data,
    rates_found, debate_result) with the correct 3-argument signature.
    """
    from .pricing_adapter import run_pricing_engine
    from ..schemas.pricing import PricingInput

    sector = entities.get("detected_sector")
    if not sector:
        logger.info("[PIPELINE] No sector detected, skipping pricing")
        return None, "estimated", "No sector detected. Pricing cannot be calculated."

    # Determine pricing mode
    has_boq = bool(boq_items)
    boq_is_reliable = boq_confidence in ("High", "Medium") if boq_confidence else False
    pricing_mode = "boq_based" if (has_boq and boq_is_reliable) else "estimated"

    # Determine cost_per_hour (from BOQ rates if available)
    cost_per_hour = 100.0  # default fallback
    cost_source = "document" if has_boq else "config"
    rates = [i.get("rate") for i in boq_items if i.get("rate") is not None]
    if rates:
        cost_per_hour = sum(rates) / len(rates)
        cost_source = "document"
        logger.info("[PIPELINE] Using average BOQ rate: %.2f", cost_per_hour)
    elif has_boq and not boq_is_reliable:
        logger.info("[PIPELINE] BOQ exists but confidence=%s, using default rate",
                    boq_confidence)

    # Use BOQ quantities to estimate worker count if available
    workforce = dict(entities.get("detected_workforce", {}))
    if not workforce and has_boq:
        estimated_workers = max(1, len(boq_items))
        workforce = {"total_workers": estimated_workers}
        logger.info("[PIPELINE] Estimated workforce from BOQ item count: %d",
                    estimated_workers)

    if not workforce:
        workforce = {"total_workers": 10}

    # Build location
    locations = entities.get("detected_locations", [])
    location = locations[0] if locations else None

    # Build requirements
    requirements = {}
    if "shifts_per_day" in workforce:
        requirements["shifts_per_day"] = workforce.pop("shifts_per_day")
    if "hours_per_day" in workforce:
        requirements["hours_per_day"] = workforce.pop("hours_per_day")
    if "days_per_week" in workforce:
        requirements["days_per_week"] = workforce.pop("days_per_week")

    try:
        pricing_input = PricingInput(
            sector=sector,
            cost_per_hour=cost_per_hour,
            cost_source=cost_source,
            duration_months=entities.get("detected_duration_months"),
            workforce=workforce if workforce else None,
            requirements=requirements if requirements else None,
            location=location,
        )

        # Call the adapter which properly handles the
        # PricingEngine.calculate(tender_data, rates_found, debate_result) signature
        result_dict, pricing_status, failure_reason = run_pricing_engine(
            pricing_input,
            rates_found=None,    # No rates_found from extraction pipeline
            debate_result=None,  # No debate_result from extraction pipeline
        )

        if pricing_status == "failed":
            logger.warning("[PIPELINE] Pricing failed: %s", failure_reason)
            return None, pricing_mode, failure_reason

        # If BOQ confidence is low, add a reliability note
        if has_boq and boq_confidence == "Low":
            result_dict["price_reliability"] = "low"
            result_dict["price_note"] = (
                "BOQ extracted with low confidence. Pricing based on estimated quantities."
            )
        elif pricing_mode == "estimated":
            result_dict["price_reliability"] = "estimated"
            result_dict["price_note"] = (
                "No BOQ data available. Pricing is estimated."
            )
        else:
            result_dict["price_reliability"] = "boq_based"
            result_dict["price_note"] = (
                "Pricing based on extracted Bill of Quantities."
            )

        logger.info(
            "[PIPELINE] Pricing calculated mode=%s sector=%s",
            pricing_mode, sector,
        )
        return result_dict, pricing_mode, None

    except Exception as e:
        logger.warning("[PIPELINE] Pricing exception: %s", e)
        return None, pricing_mode, str(e)


# ── Database helpers ────────────────────────────────────────────────


async def _create_job(job_id: str, user_id: str, filename: str, original_name: str) -> None:
    """Insert a new processing_jobs row."""
    db = await get_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """INSERT INTO processing_jobs
               (job_id, user_id, filename, original_name, status, progress, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'queued', 'pending', ?, ?)""",
            (job_id, user_id, filename, original_name, now, now),
        )
        await db.commit()
    finally:
        await close_db(db)


async def _update_job(job_id: str, **kwargs) -> None:
    """Update job fields in the database.

    Dynamically builds SET clause from kwargs.  The job_id for the WHERE
    clause and updated_at timestamp are handled automatically.

    Raises SQL errors immediately so the caller (run_pipeline) can catch
    and update the DB to 'failed' status.
    """
    if not kwargs:
        return
    sets = []
    values = []
    for key, val in kwargs.items():
        sets.append(f"{key} = ?")
        values.append(val)
    # NOTE: job_id is NOT appended to values here -- it's passed directly
    # in the execute() call below alongside updated_at.
    db = await get_db()
    try:
        await db.execute(
            f"UPDATE processing_jobs SET {', '.join(sets)}, updated_at = ? WHERE job_id = ?",
            (*values, datetime.now(timezone.utc).isoformat(), job_id),
        )
        await db.commit()
    finally:
        await close_db(db)


# ── Tender & Result DB helpers ─────────────────────────────────────


async def _create_tender_record(job_id: str, user_id: str, filename: str,
                                original_filename: str, file_hash: str,
                                mime_type: str, file_size: int) -> None:
    """Insert a tenders row with hardened fields."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO tenders
               (job_id, user_id, filename, original_filename, file_hash,
                mime_type, file_size, status, pipeline_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?)""",
            (job_id, user_id, filename, original_filename,
             file_hash, mime_type, file_size, PIPELINE_VERSION),
        )
        await db.commit()
    finally:
        await close_db(db)


async def _update_tender(job_id: str, **kwargs) -> None:
    """Update tenders row fields.

    Dynamically builds SET clause from kwargs.  The job_id for the WHERE
    clause and updated_at timestamp are handled automatically.

    Raises SQL errors immediately so the caller can handle them.
    """
    if not kwargs:
        return
    sets = []
    values = []
    for key, val in kwargs.items():
        sets.append(f"{key} = ?")
        values.append(val)
    # NOTE: job_id is NOT appended to values here -- it's passed directly
    # in the execute() call below alongside updated_at.
    db = await get_db()
    try:
        await db.execute(
            f"UPDATE tenders SET {', '.join(sets)}, updated_at = ? WHERE job_id = ?",
            (*values, datetime.now(timezone.utc).isoformat(), job_id),
        )
        await db.commit()
    finally:
        await close_db(db)


async def _store_result(tender_id: str, result: ProcessingResult,
                        pricing_mode: str) -> None:
    """Insert a tender_results row."""
    import json as _json
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO tender_results
               (tender_id, raw_text, sector, sector_confidence,
                duration_months, locations_json, workforce_json,
                schedule_json, boq_json, boq_confidence,
                pricing_json, pricing_mode, warnings_json,
                extraction_method, pipeline_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tender_id,
                result.full_text,
                result.detected_sector,
                result.boq_confidence if result.detected_sector else None,
                result.detected_duration_months,
                _json.dumps(result.detected_locations),
                _json.dumps(result.detected_workforce),
                _json.dumps(result.detected_schedule),
                _json.dumps([i.model_dump() if hasattr(i, "model_dump") else dict(i) for i in result.boq_items]),
                result.boq_confidence,
                _json.dumps(result.pricing_result),
                pricing_mode,
                _json.dumps(result.warnings),
                result.extraction_method,
                PIPELINE_VERSION,
            ),
        )
        await db.commit()
    finally:
        await close_db(db)


# ── Duplicate detection ────────────────────────────────────────────


async def _check_duplicate(file_hash: str) -> Optional[str]:
    """
    Check if a file with this SHA256 hash was already uploaded.
    Returns the existing job_id if found, None otherwise.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT job_id FROM tenders WHERE file_hash = ? LIMIT 1",
            (file_hash,),
        )
        row = await cursor.fetchone()
        if row:
            return row["job_id"]
        return None
    finally:
        await close_db(db)


# ── Main pipeline entry point ──────────────────────────────────────


async def run_pipeline(job_id: str, file_path: str, original_name: str,
                       user_id: str, file_hash: str = "",
                       mime_type: str = "", file_size: int = 0) -> None:
    """
    Execute the full 6-stage tender processing pipeline.

    Supports partial_success — if some non-critical stages fail, the job
    is marked partial_success rather than failed.  Only a complete
    pipeline crash results in status=failed.
    """
    logger.info("[PIPELINE] Starting pipeline job_id=%s file=%s version=%s",
                job_id, original_name, PIPELINE_VERSION)
    await _log_event(job_id, "upload_received", "success",
                     f"Received: {original_name}")

    # Track per-stage success for partial_success calculation
    stage_results: Dict[str, bool] = {}
    entities: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    full_text: Optional[str] = None
    boq_items: List[Dict[str, Any]] = []
    boq_confidence: Optional[str] = None
    boq_warnings: List[str] = []
    pricing_result: Optional[Dict[str, Any]] = None
    pricing_mode: str = "estimated"
    text_length: int = 0

    try:
        # ── Stage 1: Metadata ──────────────────────────────────────
        t0 = time.monotonic()
        await _update_job(job_id, status="processing", progress="metadata_extraction")
        try:
            metadata = _extract_metadata(file_path, original_name)
            stage_results["metadata_extraction"] = True
            await _record_stage(job_id, "metadata_extraction", True, str(metadata), t0)
            await _update_tender(job_id, status="processing")
        except Exception as e:
            stage_results["metadata_extraction"] = False
            await _record_stage(job_id, "metadata_extraction", False, str(e), t0)
            logger.warning("[PIPELINE] Stage 1 failed: %s", e)
            metadata = {"size_bytes": 0, "file_type": "unknown"}

        # ── Stage 2: Text extraction ───────────────────────────────
        t0 = time.monotonic()
        await _update_job(job_id, progress="document_text_extraction")
        try:
            full_text = await _extract_text(file_path, original_name)
            text_length = len(full_text) if full_text else 0
            stage_results["text_extraction"] = full_text is not None
            detail = f"{text_length} chars extracted" if full_text else "No text extracted"
            await _record_stage(job_id, "text_extraction", full_text is not None, detail, t0)
        except Exception as e:
            stage_results["text_extraction"] = False
            await _record_stage(job_id, "text_extraction", False, str(e), t0)
            logger.warning("[PIPELINE] Stage 2 failed: %s", e)

        # ── Stage 3: Entity extraction ─────────────────────────────
        t0 = time.monotonic()
        await _update_job(job_id, progress="entity_extraction")
        try:
            if full_text:
                entities = _extract_entities(full_text)
            stage_results["entity_extraction"] = True
            await _record_stage(job_id, "entity_extraction", True,
                                f"sector={entities.get('detected_sector')}", t0)
        except Exception as e:
            stage_results["entity_extraction"] = False
            await _record_stage(job_id, "entity_extraction", False, str(e), t0)
            logger.warning("[PIPELINE] Stage 3 failed: %s", e)

        # ── Stage 4: BOQ extraction ────────────────────────────────
        t0 = time.monotonic()
        await _update_job(job_id, progress="boq_analysis")
        try:
            ext = os.path.splitext(original_name)[1].lower()
            if ext == ".pdf":
                boq_items, boq_confidence, boq_warnings = await _extract_boq(file_path)
            else:
                boq_warnings.append("BOQ extraction only supported for PDF files")
            boq_ok = ext != ".pdf" or bool(boq_items) or boq_confidence in ("Medium", "High")
            stage_results["boq_analysis"] = boq_ok
            await _record_stage(job_id, "boq_analysis", boq_ok,
                                f"{len(boq_items)} items, confidence={boq_confidence}", t0)
        except Exception as e:
            stage_results["boq_analysis"] = False
            await _record_stage(job_id, "boq_analysis", False, str(e), t0)
            boq_warnings.append(f"BOQ extraction failed: {e}")

        # ── Stage 5: Pricing ───────────────────────────────────────
        t0 = time.monotonic()
        await _update_job(job_id, progress="pricing_calculation")
        pricing_unavailable_reason: Optional[str] = None
        try:
            pricing_result, pricing_mode, pricing_unavailable_reason = _run_pricing(
                entities, boq_items, boq_confidence
            )
            stage_results["pricing_calculation"] = pricing_result is not None
            pricing_detail = f"mode={pricing_mode}"
            if pricing_unavailable_reason:
                pricing_detail += f" reason={pricing_unavailable_reason}"
            await _record_stage(job_id, "pricing_calculation",
                                stage_results["pricing_calculation"],
                                pricing_detail, t0)
            if pricing_unavailable_reason:
                logger.warning("[PIPELINE] Pricing unavailable: %s",
                               pricing_unavailable_reason)
        except Exception as e:
            stage_results["pricing_calculation"] = False
            pricing_unavailable_reason = str(e)
            await _record_stage(job_id, "pricing_calculation", False, str(e), t0)

        # ── Stage 6: Finalisation ──────────────────────────────────
        t0 = time.monotonic()
        await _update_job(job_id, progress="finalising")
        warnings: List[str] = list(boq_warnings)

        stored_text = full_text[:100000] if full_text else None

        # ── Determine final status ────────────────────────────────────
        # Critical stages: metadata_extraction, text_extraction, finalisation
        # Non-critical stages: entity_extraction, boq_analysis, pricing_calculation
        core_success = stage_results.get("metadata_extraction", False) or \
                       stage_results.get("text_extraction", False)
        final_status = "completed" if core_success else "failed"
        if final_status == "completed" and not all(stage_results.values()):
            has_partial_failure = any(
                not v for k, v in stage_results.items()
                if k in ("entity_extraction", "boq_analysis", "pricing_calculation")
            )
            if has_partial_failure:
                final_status = "partial_success"
                logger.info("[PIPELINE] Job %s partial_success: stages=%s",
                            job_id, stage_results)
                warnings.append("Some processing stages had issues. Results may be incomplete.")

        # ── Build completed_stages / failed_stages lists ──────────────
        completed_stages = [s for s, ok in stage_results.items() if ok]
        failed_stages = [s for s, ok in stage_results.items() if not ok]
        # finalisation is implied by the pipeline completing
        completed_stages.append("finalisation")

        result = ProcessingResult(
            job_id=job_id,
            status=final_status,   # ← critical: use actual final status, not hardcoded "completed"
            filename=original_name,
            completed_stages=completed_stages,
            failed_stages=failed_stages,
            metadata=metadata,
            full_text=stored_text,
            text_length=text_length,
            detected_sector=entities.get("detected_sector"),
            detected_duration_months=entities.get("detected_duration_months"),
            detected_locations=entities.get("detected_locations", []),
            detected_workforce=entities.get("detected_workforce", {}),
            detected_schedule=entities.get("detected_schedule", {}),
            boq_items=[ExtractedBOQItem(**i) for i in boq_items],
            boq_confidence=boq_confidence,
            pricing_result=pricing_result,
            warnings=warnings,
            extraction_method=f"pipeline_{PIPELINE_VERSION}",
            pipeline_version=PIPELINE_VERSION,
        )

        result_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
        result_json = json.dumps(result_dict, default=str)

        now_iso = datetime.now(timezone.utc).isoformat()
        await _update_job(job_id, status=final_status, progress="done",
                          result_json=result_json)
        await _update_tender(job_id, status=final_status, completed_at=now_iso)
        await _store_result(job_id, result, pricing_mode)
        await _record_stage(job_id, "finalisation", True,
                            f"status={final_status}", t0)

        logger.info("[PIPELINE] Pipeline complete job_id=%s status=%s "
                    "completed_stages=%s failed_stages=%s",
                    job_id, final_status, completed_stages, failed_stages)

    except Exception as e:
        logger.exception("[PIPELINE] Pipeline crashed job_id=%s", job_id)
        await _update_job(job_id, status="failed", progress="error",
                          error_message=str(e))
        await _update_tender(job_id, status="failed")
        await _log_event(job_id, "finalisation", "failed", str(e))