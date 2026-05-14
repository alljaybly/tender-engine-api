"""
Pydantic schemas for Bill of Quantities (BOQ) extraction.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BOQItem(BaseModel):
    """A single line item extracted from a BOQ PDF."""
    item_no: Optional[str] = Field(default=None, description="Item number / reference")
    description: str = Field(default="", description="Item description / scope of work")
    quantity: Optional[float] = Field(default=None, description="Measured quantity")
    unit: Optional[str] = Field(default=None, description="Unit of measure (e.g. m², each, hour, lump sum)")
    rate: Optional[float] = Field(default=None, description="Unit rate in ZAR")
    amount: Optional[float] = Field(default=None, description="Extended amount (qty × rate) in ZAR")

    class Config:
        json_schema_extra = {
            "example": {
                "item_no": "1.1",
                "description": "Supply and install 50mm diameter PVC pipe",
                "quantity": 150.0,
                "unit": "m",
                "rate": 85.50,
                "amount": 12825.00,
            }
        }


class BOQTotals(BaseModel):
    """Aggregated totals extracted from a BOQ."""
    total_before_vat: Optional[float] = Field(default=None, description="Total amount excluding VAT")
    vat: Optional[float] = Field(default=None, description="VAT amount (if separately stated)")
    total_incl_vat: Optional[float] = Field(default=None, description="Total amount including VAT")
    page_count: Optional[int] = Field(default=None, description="Number of pages processed")


class BOQResult(BaseModel):
    """Full BOQ extraction result."""
    filename: str = Field(..., description="Source PDF filename")
    page_count: int = Field(..., description="Number of pages processed")
    items: List[BOQItem] = Field(default_factory=list, description="Extracted line items")
    totals: BOQTotals = Field(default_factory=BOQTotals, description="Aggregated totals")
    extraction_method: str = Field(
        ..., description="Method used: pdfplumber_tables, pdfplumber_text, camelot, or fallback_text"
    )
    confidence: str = Field(..., description="Overall confidence: High, Medium, Low")
    warnings: List[str] = Field(default_factory=list, description="Warnings or issues encountered during extraction")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "tender_boq_sample.pdf",
                "page_count": 3,
                "items": [
                    {
                        "item_no": "1.1",
                        "description": "Supply and install 50mm diameter PVC pipe",
                        "quantity": 150.0,
                        "unit": "m",
                        "rate": 85.50,
                        "amount": 12825.00,
                    }
                ],
                "totals": {
                    "total_before_vat": 975600.00,
                    "vat": 146340.00,
                    "total_incl_vat": 1121940.00,
                    "page_count": 3,
                },
                "extraction_method": "pdfplumber_tables",
                "confidence": "High",
                "warnings": [],
            }
        }


class BOQExtractRequest(BaseModel):
    """Request payload for BOQ extraction from an uploaded PDF."""
    extract_totals: bool = Field(default=True, description="Whether to attempt extracting grand totals")
    page_range: Optional[str] = Field(
        default=None,
        description="Page range to process, e.g. '1-3' or '1,3,5'. Processes all pages if None.",
    )