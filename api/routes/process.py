"""
Tender upload and processing pipeline routes.

Routes:
  POST /api/process/upload       — Upload a tender document and start async processing
  POST /api/process-tender       — Legacy endpoint (preserved)
  GET  /api/process/status/{id}  — Check processing job status
  GET  /api/process/result/{id}  — Retrieve processing job result
"""
import asyncio
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from ..schemas.process import ProcessUploadResponse, ProcessingJobStatus, ProcessingResult
from ..routes.auth import get_current_user
from ..services.database import get_db, close_db
from ..services.pipeline import (
    run_pipeline, _create_job, _update_job,
    _create_tender_record, _check_duplicate,
)
from ..services.job_store import create_job, update_job
from ..services.worker import process_job
from ..services.user_store import record_job_failure
from ..utils import error_response

logger = logging.getLogger(__name__)

# Main router (legacy / process-tender stays here)
router = APIRouter()

# Sub-router for new pipeline endpoints under /process
process_pipeline_router = APIRouter(prefix="/process")

# ── Storage directories ─────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file extensions for the new pipeline
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ── Binary/executable magic bytes ────────────────────────────────
# ELF (Linux/Unix executables)
ELF_MAGIC = b"\x7fELF"
# PE (Windows executables - PE header starts with "PE\x00\x00" at offset 0x3C)
PE_MAGIC = b"MZ"
# Mach-O (macOS executables)
MACHO_MAGIC_32 = b"\xfe\xed\xface"
MACHO_MAGIC_64 = b"\xfe\xed\xfacf"
MACHO_MAGIC_CIGAM_32 = b"\xce\xfa\xed\xfe"
MACHO_MAGIC_CIGAM_64 = b"\xcf\xfa\xed\xfe"
EXECUTABLE_MAGICS = {ELF_MAGIC, PE_MAGIC, MACHO_MAGIC_32, MACHO_MAGIC_64,
                     MACHO_MAGIC_CIGAM_32, MACHO_MAGIC_CIGAM_64}

PDF_MAGIC = b"%PDF"
DOCX_MAGIC = b"PK\x03\x04"
BOM_MAGIC = b"\xef\xbb\xbf"


def _sanitise_filename(filename: str) -> str:
    """Remove dangerous characters from a filename while preserving extension.

    Permitted characters in base name: a-z, A-Z, 0-9, underscore (_),
    hyphen (-), period (.), space ( ).
    Permitted in extension: a-z, A-Z, 0-9, and the leading period (.).
    Blocks: path traversal (..), slashes, null bytes, control characters.
    """
    # Remove path separators, null bytes, control characters upfront
    filename = re.sub(r"[/\\\x00-\x1f]", "", filename)

    name, ext = os.path.splitext(filename)

    # Keep only safe chars in the base name
    safe_name = re.sub(r"[^a-zA-Z0-9\-_\. ]", "", name)[:128]

    # Keep only safe chars in extension: letters, digits, and the leading dot
    safe_ext = re.sub(r"[^a-zA-Z0-9\.]", "", ext)[:10]

    # Block path traversal (..) in the cleaned result
    if ".." in safe_name or ".." in safe_ext:
        safe_name = "file"
        safe_ext = ".txt"

    # Block multiple dangerous extensions (e.g. .exe.pdf)
    ext_count = safe_ext.count(".")
    if ext_count > 1:
        safe_name = "file"
        safe_ext = ".txt"

    # Preserve at most one dot for extension separator
    if safe_ext and safe_ext[0] != ".":
        safe_ext = f".{safe_ext}"

    if not safe_name:
        safe_name = "file"
    if not safe_ext:
        safe_ext = ".txt"

    return f"{safe_name}{safe_ext}"


# ── File signature validation ─────────────────────────────────────`


def _is_executable(data: bytes) -> bool:
    """Check if file content matches known executable/binary magic bytes."""
    if len(data) < 4:
        return False
    # Check ELF
    if data[:4] == ELF_MAGIC:
        return True
    # Check PE (MZ header)
    if data[:2] == PE_MAGIC:
        return True
    # Check Mach-O
    header = data[:4]
    if header in (MACHO_MAGIC_32, MACHO_MAGIC_64, MACHO_MAGIC_CIGAM_32, MACHO_MAGIC_CIGAM_64):
        return True
    return False


def _is_binary_content(data: bytes, sample_size: int = 512) -> bool:
    """Detect if content is binary (non-text) by checking for null bytes
    and a high ratio of non-printable characters in the first sample_size bytes.

    This is used to reject binary files renamed as .txt.
    """
    sample = data[:sample_size]
    if not sample:
        return False

    # Null bytes are a strong indicator of binary content
    null_count = sample.count(b"\x00")

    # Count non-printable, non-whitespace control characters
    control_count = 0
    for byte in sample:
        if byte < 0x20 and byte not in (0x09, 0x0a, 0x0d):  # non-tab, non-newline, non-CR
            control_count += 1

    # Heuristic: null bytes present OR >10% control chars → likely binary
    if null_count > 0:
        return True
    if control_count > len(sample) * 0.10:
        return True
    return False


def _validate_file_signature(data: bytes, ext: str) -> tuple[bool, str]:
    """Strict file signature validation.

    Returns (is_valid, error_message).
    Rejects executable/binary files renamed to look like documents.
    """
    # Step 1: Reject executables regardless of extension
    if _is_executable(data):
        return False, "Executable files are not allowed."

    # Step 2: Validate by extension
    if ext == ".pdf":
        if data[:4] != PDF_MAGIC:
            return False, "File does not have a valid PDF signature."
        return True, ""

    if ext == ".docx":
        if data[:4] != DOCX_MAGIC:
            return False, "File does not have a valid DOCX (ZIP) signature."
        return True, ""

    if ext == ".txt":
        # Reject binary files renamed as .txt
        if _is_binary_content(data):
            return False, "Binary files are not allowed as .txt."
        return True, ""

    # Unknown extension (should not happen if called after extension check)
    return False, f"Unsupported file extension: {ext}"


# ── MIME detection helpers ─────────────────────────────────────────


def _detect_mime_from_bytes(data: bytes, ext: str) -> str:
    """Detect MIME type from file magic bytes, with extension fallback."""
    if data[:4] == PDF_MAGIC:
        return "application/pdf"
    if data[:4] == DOCX_MAGIC:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if data[:3] == BOM_MAGIC or ext == ".txt":
        return "text/plain"
    # Generic fallback
    mime_map = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
    }
    return mime_map.get(ext, "application/octet-stream")


def _mime_matches_extension(mime: str, ext: str) -> bool:
    """Check if detected MIME type is consistent with file extension."""
    ext_to_mime = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
    }
    expected = ext_to_mime.get(ext)
    if expected and mime != expected:
        # Allow ZIP container for DOCX (PK magic bytes)
        if ext == ".docx" and mime.startswith("application/"):
            return True
        return False
    return True


# ── Legacy endpoint (preserved) ────────────────────────────────────


@router.post('/process-tender')
async def process_tender(request: Request, file: UploadFile = File(...), cost_per_hour: Optional[float] = Form(None)):
    if cost_per_hour is not None and cost_per_hour <= 0:
        return error_response("validation_error", "cost_per_hour must be greater than 0", 422)

    job_id = uuid.uuid4().hex
    user = getattr(request.state, 'user', {})
    logger.info("[PROCESS] Received file for job %s user=%s filename=%s", job_id, user.get('user_id'), file.filename)

    # save file
    suffix = Path(file.filename).suffix or ''
    out_path = UPLOAD_DIR / f"{job_id}{suffix}"
    try:
        contents = await file.read()
        with open(out_path, 'wb') as f:
            f.write(contents)
    except Exception as e:
        logger.exception("[PROCESS] Failed to save uploaded file: %s", e)
        record_job_failure(user.get('api_key'))
        raise HTTPException(status_code=500, detail='Failed to save uploaded file')

    create_job(job_id)
    update_job(
        job_id,
        api_key=user.get('api_key'),
        user={'user_id': user.get('user_id'), 'email': user.get('email')}
    )

    # Use default cost_per_hour if not provided
    final_cost_per_hour = cost_per_hour if cost_per_hour is not None else 100.0

    # Launch background task
    asyncio.create_task(process_job(job_id, str(out_path), final_cost_per_hour))

    return {
        "job_id": job_id,
        "status": "queued"
    }


# ── New pipeline endpoints (under sub-router with /process prefix) ─


@process_pipeline_router.post(
    "/upload",
    response_model=ProcessUploadResponse,
    summary="Upload a tender document for processing",
    description=(
        "Upload a tender document (PDF, DOCX, or TXT). "
        "The file is validated, stored, and a background processing pipeline is started. "
        "Returns a job_id that can be used to poll status and retrieve results."
    ),
)
async def process_upload(
    file: UploadFile = File(..., description="Tender document file (PDF, DOCX, or TXT)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a tender document for async processing.

    - **file**: PDF, DOCX, or TXT file (required)
    - **Returns**: `job_id` for status polling and result retrieval
    """
    # ── Step 1: Basic validation ────────────────────────────────────
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided.",
        )

    # ── Step 2: Sanitise filename ───────────────────────────────────
    original_name = _sanitise_filename(file.filename)
    if original_name != file.filename:
        logger.info("[UPLOAD] Sanitised filename: %s -> %s", file.filename, original_name)

    # ── Step 3: Path traversal check ────────────────────────────────
    if ".." in file.filename or "/" in file.filename.replace("\\", "/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    # ── Step 4: Extension validation ────────────────────────────────
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # ── Read file contents ──────────────────────────────────────────
    job_id = uuid.uuid4().hex
    safe_filename = f"{job_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    user_email = current_user.get("email", "unknown")

    try:
        contents = await file.read()

        # ── Step 5: File size check ─────────────────────────────────
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
            )

        # ── Step 6: Executable detection (before any signature check) ──
        if _is_executable(contents):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Executable files are not allowed.",
            )

        # ── Step 7: File signature validation ───────────────────────
        sig_valid, sig_error = _validate_file_signature(contents, ext)
        if not sig_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=sig_error,
            )

        # ── Step 8: MIME type detection & cross-check ───────────────
        mime_type = _detect_mime_from_bytes(contents, ext)
        if not _mime_matches_extension(mime_type, ext):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type mismatch: declared extension '{ext}' "
                       f"does not match detected content type '{mime_type}'.",
            )

        # ── Step 9: Binary content detection for TXT ────────────────
        if ext == ".txt" and _is_binary_content(contents):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Binary files are not allowed as .txt.",
            )

        # ── Compute SHA256 hash ─────────────────────────────────────
        import hashlib
        file_hash = hashlib.sha256(contents).hexdigest()

        # ── Duplicate detection ─────────────────────────────────────
        existing_job = await _check_duplicate(file_hash)
        if existing_job:
            logger.info(
                "[UPLOAD] Duplicate detected: hash=%s existing=%s new=%s",
                file_hash, existing_job, job_id,
            )

        with open(file_path, "wb") as f:
            f.write(contents)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[UPLOAD] Failed to save file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file.",
        )

    # ── Create DB job record ────────────────────────────────────────
    try:
        await _create_job(
            job_id=job_id,
            user_id=user_email,
            filename=safe_filename,
            original_name=original_name,
        )
        await _create_tender_record(
            job_id=job_id,
            user_id=user_email,
            filename=safe_filename,
            original_filename=original_name,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size=len(contents),
        )
    except Exception as e:
        logger.exception("[UPLOAD] Failed to create DB records: %s", e)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job record.",
        )

    # ── Log duplicate warning ───────────────────────────────────────
    warnings_list = []
    if existing_job:
        warnings_list.append(f"Duplicate file detected. Previously uploaded as job {existing_job}")

    # ── Launch background pipeline ──────────────────────────────────
    asyncio.create_task(
        run_pipeline(
            job_id, file_path, original_name, user_email,
            file_hash=file_hash, mime_type=mime_type, file_size=len(contents),
        )
    )

    response = ProcessUploadResponse(
        job_id=job_id,
        status="queued",
        filename=original_name,
        message="File uploaded and queued for processing",
    )
    if warnings_list:
        response.message += f" Warnings: {'; '.join(warnings_list)}"

    return response


@process_pipeline_router.get(
    "/status/{job_id}",
    response_model=ProcessingJobStatus,
    summary="Get processing job status",
    description="Check the current status of a processing job by its job_id.",
)
async def process_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Poll job status by job_id.

    - **job_id**: UUID4 hex string returned from POST /api/process/upload
    - **Returns**: Current status (queued, processing, extracting, boq_analysis, pricing, completed, failed)
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT job_id, status, progress, created_at, updated_at, error_message "
            "FROM processing_jobs WHERE job_id = ?",
            (job_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )

        job = dict(row)
        return ProcessingJobStatus(
            job_id=job["job_id"],
            status=job["status"],
            progress=job["progress"],
            created_at=job["created_at"],
            updated_at=job["updated_at"],
            error_message=job["error_message"],
        )
    finally:
        await close_db(db)


@process_pipeline_router.get(
    "/result/{job_id}",
    response_model=ProcessingResult,
    summary="Get processing job result",
    description=(
        "Retrieve the full processing result for a completed or partial_success job. "
        "Returns all successfully extracted data (sector, duration, workforce, "
        "locations, BOQ items, etc.) even if some stages failed. "
        "Failed jobs return a structured failure response with error details."
    ),
)
async def process_result(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve the full processing result by job_id.

    Allowed statuses:
      - `completed`:      Return full result with all stages
      - `partial_success`: Return partial result with completed/failed stage lists
      - `failed`:          Return structured failure response

    Blocked statuses:
      - `queued`, `processing` → 200 with status detail message
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT job_id, status, filename, result_json, error_message "
            "FROM processing_jobs WHERE job_id = ?",
            (job_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found.",
            )

        job = dict(row)
        job_status = job["status"]

        # ── Blocked: still processing ──────────────────────────────
        if job_status in ("queued", "processing"):
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail=f"Job is still {job_status}. Poll GET /api/process/status/{job_id} for updates.",
            )

        # ── Failed: structured failure response ─────────────────────
        if job_status == "failed":
            error_msg = job.get("error_message", "Unknown pipeline error")
            if error_msg:
                logger.warning("[RESULT] Returning failed result for %s: %s",
                               job_id, error_msg)
            return ProcessingResult(
                job_id=job["job_id"],
                status="failed",
                filename=job.get("filename"),
                warnings=[error_msg] if error_msg else [],
            )

        # ── Allowed: completed / partial_success ───────────────────
        if job_status not in ("completed", "partial_success"):
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail=f"Job is in unexpected state '{job_status}'.",
            )

        if not job.get("result_json"):
            logger.error("[RESULT] %s job '%s' has no result_json stored",
                         job_status, job_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Job is marked {job_status} but no result data was stored.",
            )

        # ── Parse stored JSON result ───────────────────────────────
        try:
            result_dict = json.loads(job["result_json"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.exception("[RESULT] Failed to parse result_json for job %s", job_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to parse stored result: {e}",
            )

        # ── Override stored status with actual DB job status ────────
        # The pipeline may have stored "completed" in result_json before
        # it determined the final status was "partial_success".  The DB
        # job status is the source of truth.
        result_dict["status"] = job_status

        # ── Inject pricing_status from pricing_result ─────────────
        if job_status == "partial_success" and result_dict.get("pricing_result") is None:
            result_dict["pricing_status"] = "failed"
            result_dict["pricing_unavailable_reason"] = (
                "Pricing could not be calculated due to missing or insufficient data."
            )
        elif result_dict.get("pricing_result") is not None:
            result_dict["pricing_status"] = "completed"
        else:
            result_dict["pricing_status"] = result_dict.get("pricing_status", None)

        # ── Build completed_stages / failed_stages ─────────────────
        result_dict["completed_stages"] = result_dict.get("completed_stages", [])
        result_dict["failed_stages"] = result_dict.get("failed_stages", [])

        if not result_dict["completed_stages"]:
            inferred_completed = []
            inferred_failed = []
            stage_map = [
                ("metadata", lambda r: bool(r.get("metadata"))),
                ("text_extraction", lambda r: r.get("full_text") is not None),
                ("entity_extraction", lambda r: r.get("detected_sector") is not None),
                ("boq_analysis", lambda r: bool(r.get("boq_items"))),
                ("pricing_calculation", lambda r: r.get("pricing_result") is not None),
            ]
            for stage_name, checker in stage_map:
                if checker(result_dict):
                    inferred_completed.append(stage_name)
                else:
                    inferred_failed.append(stage_name)
            inferred_completed.append("finalisation")
            result_dict["completed_stages"] = inferred_completed
            result_dict["failed_stages"] = inferred_failed

        # ── Validation guard: status MUST match stage results ───────
        # If failed_stages is non-empty, status cannot be "completed"
        if result_dict["failed_stages"] and result_dict["status"] == "completed":
            logger.warning("[STATUS] Corrected inconsistent completed state "
                           "to partial_success for job %s: failed_stages=%s",
                           job_id, result_dict["failed_stages"])
            result_dict["status"] = "partial_success"

        # ── Log explicit return type ───────────────────────────────
        if job_status == "partial_success":
            logger.info("[RESULT] Returning partial_success result for job_id=%s: "
                        "pricing_result=%s, completed=%s, failed=%s",
                        job_id,
                        "present" if result_dict.get("pricing_result") else "absent",
                        result_dict.get("completed_stages"),
                        result_dict.get("failed_stages"))

        logger.info("[RESULT] Returning %s result for job %s: "
                    "completed_stages=%s, failed_stages=%s",
                    result_dict["status"], job_id,
                    result_dict.get("completed_stages"),
                    result_dict.get("failed_stages"))

        return ProcessingResult(**result_dict)

    finally:
        await close_db(db)
