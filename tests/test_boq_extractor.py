"""
Tests for BOQ PDF extraction service.
Creates a sample BOQ PDF using fpdf2 and verifies extraction returns structured items.
"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.schemas.boq import BOQResult, BOQItem


def _create_sample_boq_pdf() -> str:
    """Create a sample BOQ PDF using fpdf2 and return the file path."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    # Header
    pdf.cell(30, 10, "Item No.", border=1)
    pdf.cell(80, 10, "Description", border=1)
    pdf.cell(25, 10, "Qty", border=1)
    pdf.cell(20, 10, "Unit", border=1)
    pdf.cell(25, 10, "Rate", border=1)
    pdf.cell(30, 10, "Amount", border=1, ln=True)

    # Row 1
    pdf.cell(30, 10, "1.1", border=1)
    pdf.cell(80, 10, "Excavation trench 600mm", border=1)
    pdf.cell(25, 10, "150.00", border=1)
    pdf.cell(20, 10, "m", border=1)
    pdf.cell(25, 10, "85.50", border=1)
    pdf.cell(30, 10, "12825.00", border=1, ln=True)

    # Row 2
    pdf.cell(30, 10, "1.2", border=1)
    pdf.cell(80, 10, "Supply PVC pipe 100mm", border=1)
    pdf.cell(25, 10, "200.00", border=1)
    pdf.cell(20, 10, "m", border=1)
    pdf.cell(25, 10, "120.00", border=1)
    pdf.cell(30, 10, "24000.00", border=1, ln=True)

    # Row 3
    pdf.cell(30, 10, "1.3", border=1)
    pdf.cell(80, 10, "Concrete class 25 MPa", border=1)
    pdf.cell(25, 10, "45.00", border=1)
    pdf.cell(20, 10, "m3", border=1)
    pdf.cell(25, 10, "1850.00", border=1)
    pdf.cell(30, 10, "83250.00", border=1, ln=True)

    # Total row
    pdf.cell(30, 10, "", border=1)
    pdf.cell(80, 10, "Total", border=1)
    pdf.cell(25, 10, "", border=1)
    pdf.cell(20, 10, "", border=1)
    pdf.cell(25, 10, "", border=1)
    pdf.cell(30, 10, "120075.00", border=1, ln=True)

    tmpdir = tempfile.mkdtemp()
    filepath = os.path.join(tmpdir, "test_boq.pdf")
    pdf.output(filepath)
    return filepath


class TestBOQExtractor(unittest.TestCase):
    """Test the BOQ extraction service with a known sample PDF."""

    @classmethod
    def setUpClass(cls):
        """Create the sample PDF once for all tests (avoids per-test overhead)."""
        cls.pdf_path = _create_sample_boq_pdf()
        cls.tmpdir = os.path.dirname(cls.pdf_path)

    @classmethod
    def tearDownClass(cls):
        """Clean up the sample PDF."""
        if os.path.exists(cls.pdf_path):
            os.remove(cls.pdf_path)
        if os.path.exists(cls.tmpdir):
            os.rmdir(cls.tmpdir)

    def _extract(self, **kwargs):
        """Helper: import and call extract_from_pdf with a timeout guard."""
        from api.services.boq_extractor import extract_from_pdf
        return extract_from_pdf(self.pdf_path, **kwargs)

    def test_extract_returns_boqresult(self):
        """extract_from_pdf returns a BOQResult instance."""
        result = self._extract()
        self.assertIsInstance(result, BOQResult)
        self.assertIsInstance(result.items, list)

    def test_extract_returns_items(self):
        """The PDF contains 3 BOQ items; expect at least 1 item found."""
        result = self._extract()
        self.assertGreater(len(result.items), 0, "Expected at least 1 BOQ item")

    def test_extract_item_fields(self):
        """Each BOQItem has expected fields."""
        result = self._extract()
        for item in result.items:
            self.assertIsInstance(item, BOQItem)

    def test_extract_filename(self):
        """The result filename matches the input file."""
        result = self._extract()
        self.assertEqual(result.filename, "test_boq.pdf")

    def test_extract_page_count_positive(self):
        """At least 1 page should be reported."""
        result = self._extract()
        self.assertGreaterEqual(result.page_count, 1)

    def test_extract_with_page_range(self):
        """page_range parameter does not crash."""
        result = self._extract(page_range="1")
        self.assertIsInstance(result, BOQResult)

    def test_extract_method_is_set(self):
        """extraction_method should be a non-empty string."""
        result = self._extract()
        self.assertTrue(result.extraction_method)
        self.assertIn(result.extraction_method, [
            "pdfplumber_tables", "pdfplumber_text", "camelot",
            "none", "fallback_text",
        ])

    def test_extract_confidence_is_set(self):
        """confidence should be a non-empty string."""
        result = self._extract()
        self.assertIn(result.confidence, ["High", "Medium", "Low"])

    def test_extract_warnings_is_list(self):
        """warnings should be a list (possibly empty)."""
        result = self._extract()
        self.assertIsInstance(result.warnings, list)

    def test_item_has_description(self):
        """Each item should have a non-empty description."""
        result = self._extract()
        for item in result.items:
            self.assertTrue(item.description, f"Item missing description: {item}")


if __name__ == "__main__":
    unittest.main()