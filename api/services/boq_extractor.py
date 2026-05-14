"""
Bill of Quantities (BOQ) extraction service.

Extracts line items (item_no, description, quantity, unit, rate, amount)
from South African tender BOQ PDFs using a multi-strategy approach:

1. pdfplumber table extraction (for well-structured tables)
2. camelot-py lattice/flavour (for PDFs with explicit table borders)
3. pdfplumber text-based parsing (heuristic fallback for scanned-like or malformed)
4. Raw text fallback (when all table methods fail)

Logs extraction confidence and warnings at each step.
"""
from __future__ import annotations

import logging
import re
import io
from typing import Any, Dict, List, Optional, Tuple

from ..schemas.boq import BOQItem, BOQResult, BOQTotals

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────

_NUMERIC_RE = re.compile(r"^[\d,\.\s]+$")
_CURRENCY_RE = re.compile(r"^[Rr]?\s*[\d,\.\s]+$")
_ITEM_NO_RE = re.compile(
    r"^(\d+(?:\.\d+)*)\s+"  # "1.1  " or "1.1.2  "
)


def _parse_float(raw: Any) -> Optional[float]:
    """Safely parse a number from a cell / string."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    cleaned = re.sub(r"[Rr\s,\-]", "", str(raw).strip().replace("\xa0", " "))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _is_numeric_cell(val: Any) -> bool:
    """Check if a cell value looks numeric (could be qty, rate, or amount)."""
    if val is None:
        return False
    if isinstance(val, (int, float)):
        return True
    s = str(val).strip().replace("\xa0", " ")
    if not s:
        return False
    return bool(_CURRENCY_RE.match(s) or _NUMERIC_RE.match(s))


def _parse_page_range(page_range: Optional[str], max_pages: int) -> List[int]:
    """Convert user-supplied page range spec to list of 0-indexed page numbers."""
    if not page_range:
        return list(range(max_pages))
    pages: List[int] = []
    for part in page_range.split(","):
        part = part.strip()
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                start, end = int(a.strip()), int(b.strip())
                pages.extend(range(start, end + 1))
            except ValueError:
                logger.warning("Invalid page range part: %s", part)
                continue
        else:
            try:
                pages.append(int(part))
            except ValueError:
                logger.warning("Invalid page number: %s", part)
                continue
    # Deduplicate, sort, clamp to 0-indexed
    return sorted(set(p for p in pages if 1 <= p <= max_pages))


# ── Parser state machine helpers ────────────────────────────────────

_BOQ_COLUMN_KEYWORDS = {
    "item", "no", "ref", "number",
    "description", "item", "work", "scope",
    "quantity", "qty", "qnty",
    "unit", "uom", "measure",
    "rate", "price", "unit price",
    "amount", "total", "extended",
}


def _classify_header(row: List[str]) -> Optional[Dict[str, int]]:
    """
    Attempt to map column names to BOQ fields.
    Returns e.g. {"item_no": 0, "description": 1, "quantity": 2, ...}
    """
    mapping: Dict[str, int] = {}
    lowered = [str(c).strip().lower() for c in row if c is not None]
    for idx, col in enumerate(lowered):
        col_lower = col.strip()
        if col_lower in ("item", "no", "item no", "item no.", "#"):
            mapping["item_no"] = idx
        elif "description" in col_lower or "item" in col_lower and idx not in (
            mapping.get("item_no", -1),
            mapping.get("rate", -1),
            mapping.get("amount", -1),
        ):
            mapping["description"] = idx
        elif col_lower in ("quantity", "qty", "qnty", "quant"):
            mapping["quantity"] = idx
        elif col_lower in ("unit", "uom", "measure", "unit of measure"):
            mapping["unit"] = idx
        elif col_lower in ("rate", "price", "unit price", "rate/unit"):
            mapping["rate"] = idx
        elif col_lower in ("amount", "total", "extended", "amount (z ar)",
                           "amount (zar)", "total amount"):
            mapping["amount"] = idx
    return mapping if mapping else None


def _row_to_boq_item(row: List[str], mapping: Dict[str, int]) -> Optional[BOQItem]:
    """Convert a table row to a BOQItem using the column mapping."""
    # Skip empty rows
    cleaned = [str(c).strip() for c in row if c is not None]
    if not cleaned or all(c == "" for c in cleaned):
        return None

    item_no = mapping.get("item_no")
    desc_idx = mapping.get("description")
    qty_idx = mapping.get("quantity")
    unit_idx = mapping.get("unit")
    rate_idx = mapping.get("rate")
    amt_idx = mapping.get("amount")

    # Try to extract item_no from first column if not mapped
    item_no_val: Optional[str] = None
    if item_no is not None and item_no < len(row):
        item_no_val = str(row[item_no]).strip()

    # If no explicit item_no column, attempt heuristic from first cell
    if not item_no_val and row:
        first = str(row[0]).strip() if row[0] else ""
        m = _ITEM_NO_RE.match(first)
        if m:
            item_no_val = m.group(1)

    description_val: str = ""
    if desc_idx is not None and desc_idx < len(row):
        description_val = str(row[desc_idx]).strip()
    elif row:
        # Fallback: combine non-numeric cells
        parts = []
        for i, c in enumerate(row):
            if c is not None:
                cell = str(c).strip()
                if cell and not _is_numeric_cell(cell) and i != item_no:
                    parts.append(cell)
        description_val = " ".join(parts)

    quantity_val = _parse_float(row[qty_idx]) if qty_idx is not None and qty_idx < len(row) else None
    unit_val = str(row[unit_idx]).strip() if unit_idx is not None and unit_idx < len(row) else None
    rate_val = _parse_float(row[rate_idx]) if rate_idx is not None and rate_idx < len(row) else None
    amount_val = _parse_float(row[amt_idx]) if amt_idx is not None and amt_idx < len(row) else None

    # Skip rows that are all blank
    if not description_val and item_no_val is None and quantity_val is None:
        return None

    return BOQItem(
        item_no=item_no_val,
        description=description_val,
        quantity=quantity_val,
        unit=unit_val,
        rate=rate_val,
        amount=amount_val,
    )


# ── Main extraction pipeline ────────────────────────────────────────


def extract_from_pdf(file_path: str, extract_totals: bool = True,
                     page_range: Optional[str] = None) -> BOQResult:
    """
    Extract BOQ data from a PDF file.

    Args:
        file_path: Path to the PDF file.
        extract_totals: Whether to attempt extracting grand totals.
        page_range: Optional page range spec e.g. "1-3" or "1,3,5".

    Returns:
        BOQResult with extracted items, totals, confidence, and warnings.
    """
    import os

    filename = os.path.basename(file_path)
    warnings: List[str] = []
    items: List[BOQItem] = []
    totals = BOQTotals()
    extraction_method = "none"
    confidence = "Low"
    logger.info("[BOQ] Starting extraction for %s", filename)

    # ── Phase 1: Try pdfplumber table extraction ──────────────
    try:
        pdfplumber_result, pdfplumber_ok = _try_pdfplumber_tables(
            file_path, page_range
        )
        if pdfplumber_ok:
            items = pdfplumber_result["items"]
            totals = pdfplumber_result["totals"]
            extraction_method = "pdfplumber_tables"
            if items:
                confidence = "High"
            logger.info(
                "[BOQ] pdfplumber tables extracted %d items (confidence=High)",
                len(items),
            )
            return _build_result(filename, items, totals, extraction_method, confidence, warnings)
        elif pdfplumber_result.get("partial"):
            items = pdfplumber_result["items"]
            warnings.append("Partial extraction: some pages had no tables detected by pdfplumber")
            logger.info("[BOQ] Partial pdfplumber extraction: %d items", len(items))
    except Exception as e:
        logger.warning("[BOQ] pdfplumber table extraction failed: %s", e)
        warnings.append(f"pdfplumber tables failed: {e}")

    # ── Phase 2: Try camelot lattice ──────────────────────────
    try:
        camelot_result, camelot_ok = _try_camelot(file_path, page_range)
        if camelot_ok:
            items = camelot_result["items"]
            totals = camelot_result["totals"]
            extraction_method = "camelot"
            confidence = "High" if items else "Low"
            logger.info(
                "[BOQ] camelot extracted %d items (confidence=%s)",
                len(items), confidence,
            )
            return _build_result(filename, items, totals, extraction_method, confidence, warnings)
        elif camelot_result.get("partial"):
            items = camelot_result["items"]
            warnings.append("Partial camelot extraction")
    except Exception as e:
        logger.warning("[BOQ] camelot extraction failed: %s", e)
        warnings.append(f"camelot failed: {e}")

    # ── Phase 3: Fallback text-based parsing ──────────────────
    try:
        text_result = _try_text_fallback(file_path, page_range)
        if text_result["items"]:
            items = text_result["items"]
            totals = text_result["totals"]
            extraction_method = "pdfplumber_text"
            confidence = "Medium"
            logger.info(
                "[BOQ] Fallback text parsing extracted %d items (confidence=Medium)",
                len(items),
            )
        else:
            warnings.append("No BOQ tables or items could be extracted from the PDF.")
            logger.warning("[BOQ] All extraction methods produced zero items.")
    except Exception as e:
        logger.warning("[BOQ] Fallback text parsing also failed: %s", e)
        warnings.append(f"All extraction methods failed: {e}")

    return _build_result(filename, items, totals, extraction_method, confidence, warnings)


# ── Strategy implementations ────────────────────────────────────────


def _try_pdfplumber_tables(file_path: str, page_range: Optional[str] = None) -> Tuple[Dict, bool]:
    """
    Attempt extraction using pdfplumber's .find_tables().
    Returns (result_dict, success_bool).
    """
    import pdfplumber

    items: List[BOQItem] = []
    totals = BOQTotals()
    total_before_vat: Optional[float] = None
    vat: Optional[float] = None
    total_incl_vat: Optional[float] = None
    page_count = 0

    with pdfplumber.open(file_path) as pdf:
        pages_to_process = _parse_page_range(page_range, len(pdf.pages))
        for page_num in pages_to_process:
            page = pdf.pages[page_num - 1]
            page_count += 1

            tables = page.find_tables()
            if not tables:
                logger.debug("[BOQ] Page %d: no tables found by pdfplumber", page_num)
                continue

            for table in tables:
                data = table.extract()
                if not data or len(data) < 2:
                    continue

                # First non-empty row is likely the header
                header_row = data[0]
                mapping = _classify_header(header_row)

                if mapping is None:
                    # No header detected – try to guess columns from number of numeric cells
                    mapping = _guess_mapping(data[1:] if len(data) > 1 else data)
                    start_row = 1 if len(data) > 1 else 0
                else:
                    start_row = 1

                for row in data[start_row:]:
                    if row is None:
                        continue
                    item = _row_to_boq_item(row, mapping)
                    if item is not None:
                        # Try to detect totals row
                        desc_lower = item.description.lower().strip()
                        if desc_lower in (
                            "total", "subtotal", "grand total",
                            "vat", "total excl vat", "total incl vat",
                            "total ex vat", "total inc vat",
                        ):
                            _accumulate_total(desc_lower, item, total_before_vat)
                            continue
                        items.append(item)

    if not items and page_count > 0:
        return {"items": [], "totals": totals, "partial": False}, False

    totals = BOQTotals(
        total_before_vat=total_before_vat,
        vat=vat,
        total_incl_vat=total_incl_vat,
        page_count=page_count,
    )
    return {"items": items, "totals": totals, "partial": True}, len(items) > 0


def _try_camelot(file_path: str, page_range: Optional[str] = None) -> Tuple[Dict, bool]:
    """
    Attempt extraction using camelot-py lattice flavour.
    Returns (result_dict, success_bool).
    """
    import camelot

    items: List[BOQItem] = []
    total_before_vat: Optional[float] = None
    vat: Optional[float] = None
    total_incl_vat: Optional[float] = None
    page_count = 0

    try:
        tables = camelot.read_pdf(file_path, flavor="lattice", pages="all")
    except Exception:
        try:
            tables = camelot.read_pdf(file_path, flavor="stream", pages="all")
        except Exception as e:
            logger.warning("[BOQ] camelot read failed entirely: %s", e)
            return {"items": [], "totals": BOQTotals()}, False

    if tables.n == 0:
        return {"items": [], "totals": BOQTotals()}, False

    for table in tables:
        page_count += 1
        data = table.df.values.tolist()

        if len(data) < 2:
            continue

        header_row = [str(c).strip() for c in data[0]]
        mapping = _classify_header(header_row)
        if mapping is None:
            mapping = _guess_mapping(data[1:] if len(data) > 1 else data)
            start_row = 1 if len(data) > 1 else 0
        else:
            start_row = 1

        for row_data in data[start_row:]:
            row = [str(c).strip() for c in row_data]
            item = _row_to_boq_item(row, mapping)
            if item is not None:
                desc_lower = item.description.lower().strip()
                if desc_lower in (
                    "total", "subtotal", "grand total",
                    "vat", "total excl vat", "total incl vat",
                    "total ex vat", "total inc vat",
                ):
                    _accumulate_total(desc_lower, item, total_before_vat)
                    continue
                items.append(item)

    if items:
        return {
            "items": items,
            "totals": BOQTotals(
                total_before_vat=total_before_vat,
                vat=vat,
                total_incl_vat=total_incl_vat,
                page_count=page_count,
            ),
        }, True

    return {"items": [], "totals": BOQTotals()}, False


def _try_text_fallback(file_path: str, page_range: Optional[str] = None) -> Dict:
    """
    Fallback: extract all text via pdfplumber, then try to find
    structured lines that look like BOQ items using regex heuristics.
    """
    import pdfplumber

    items: List[BOQItem] = []
    total_before_vat: Optional[float] = None
    vat: Optional[float] = None
    total_incl_vat: Optional[float] = None
    page_count = 0

    with pdfplumber.open(file_path) as pdf:
        pages_to_process = _parse_page_range(page_range, len(pdf.pages))
        for page_num in pages_to_process:
            page = pdf.pages[page_num - 1]
            page_count += 1
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                item = _parse_line_as_boq_item(line)
                if item is not None:
                    items.append(item)

    return {
        "items": items,
        "totals": BOQTotals(
            total_before_vat=total_before_vat,
            vat=vat,
            total_incl_vat=total_incl_vat,
            page_count=page_count,
        ),
    }


# ── Heuristic line parsing (text fallback) ──────────────────────────

_BOQ_LINE_RE = re.compile(
    r"^(?:\s*(\d+(?:\.\d+)*)\s+)?"
    r"(.*?)\s+"
    r"(\d[\d\.,]*)\s*"        # quantity
    r"(\w+)\s+"               # unit
    r"([\d\.,]+)\s*"          # rate
    r"([\d\.,]+)\s*$"         # amount
)

_VARIANT_LINE_RE = re.compile(
    r"^(?:\s*(\d+(?:\.\d+)*)\s+)?"
    r"(.*?)\s+"
    r"([\d\.,]+)\s*$"         # final numeric value (could be amount)
)


def _parse_line_as_boq_item(line: str) -> Optional[BOQItem]:
    """
    Heuristic: try to match a text line as a BOQ item.
    Looks for patterns like:
       1.1  Description text  150  m  85.50  12825.00
    or with only item_no + description + amount.
    """
    # Skip lines that are clearly not BOQ items
    lower = line.lower()
    if any(
        kw in lower
        for kw in ("page", "date", "ref:", "project", "contract",
                   "issued by", "prepared by", "notes:", "signature")
    ):
        return None

    m = _BOQ_LINE_RE.match(line)
    if m:
        item_no = m.group(1) if m.group(1) and m.group(1).strip() else None
        description = m.group(2).strip()
        quantity = _parse_float(m.group(3))
        unit = m.group(4).strip()
        rate = _parse_float(m.group(5))
        amount = _parse_float(m.group(6))
        if description and (quantity or amount):
            return BOQItem(
                item_no=item_no,
                description=description,
                quantity=quantity,
                unit=unit,
                rate=rate,
                amount=amount,
            )

    # Fallback: try variant with just item_no + description + amount
    vm = _VARIANT_LINE_RE.match(line)
    if vm:
        item_no = vm.group(1) if vm.group(1) and vm.group(1).strip() else None
        description = vm.group(2).strip()
        amount = _parse_float(vm.group(3))
        if description and amount and not _is_header_like(description):
            return BOQItem(item_no=item_no, description=description, amount=amount)

    return None


def _is_header_like(text: str) -> bool:
    """Return True if text looks like a column header, not a data row."""
    lower = text.lower().strip()
    headers = {"description", "item", "quantity", "qty", "unit price",
               "rate", "amount", "total", "grand total", "vat",
               "subtotal", "excl vat", "incl vat"}
    return lower in headers or any(h in lower for h in headers)


# ── Misc helpers ────────────────────────────────────────────────────


def _guess_mapping(rows: List[List[str]]) -> Dict[str, int]:
    """
    When no header is detected, guess column roles by analysing
    the type of data in each column across multiple rows.
    """
    if not rows or not rows[0]:
        return {}
    num_cols = max(len(r) for r in rows) if rows else 0
    mapping: Dict[str, int] = {}
    for col_idx in range(num_cols):
        col_values = []
        for row in rows:
            if col_idx < len(row) and row[col_idx] is not None:
                col_values.append(str(row[col_idx]).strip())
        if not col_values:
            continue
        numeric_count = sum(1 for v in col_values if _is_numeric_cell(v))
        total = len(col_values)

        # Column with >80% numeric values → likely quantity, rate, or amount
        if numeric_count / max(total, 1) > 0.8:
            if "quantity" not in mapping:
                mapping["quantity"] = col_idx
            elif "rate" not in mapping:
                mapping["rate"] = col_idx
            elif "amount" not in mapping:
                mapping["amount"] = col_idx
        else:
            # Text-heavy column → description
            if "description" not in mapping:
                mapping["description"] = col_idx
    return mapping


def _accumulate_total(label: str, item: BOQItem, total_before_vat: Optional[float]) -> None:
    """Accumulate total values from a totals row. (Stub – currently just logs."""
    logger.debug("[BOQ] Totals row skipped (not yet computed): %s -> %s", label, item.amount)


def _build_result(
    filename: str,
    items: List[BOQItem],
    totals: BOQTotals,
    extraction_method: str,
    confidence: str,
    warnings: List[str],
) -> BOQResult:
    """Assemble the final BOQResult."""
    page_count = totals.page_count or 0
    return BOQResult(
        filename=filename,
        page_count=page_count,
        items=items,
        totals=totals,
        extraction_method=extraction_method,
        confidence=confidence,
        warnings=warnings,
    )