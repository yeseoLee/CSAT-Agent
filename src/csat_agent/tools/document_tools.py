from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_core.tools import StructuredTool

try:
    import fitz
except ImportError:  # pragma: no cover - optional dependency at runtime
    fitz = None

try:
    import pytesseract
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency at runtime
    pytesseract = None
    Image = None


@dataclass
class DocumentToolWrapper:
    """Wrapper around PDF parsing and OCR operations."""

    default_dpi: int = 300
    ocr_lang: str = "kor+eng"

    def detect_pdf_type(self, pdf_path: str) -> str:
        if fitz is None:
            return "unknown"

        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            if page_count == 0:
                return "unknown"

            text_pages = 0
            for page in doc:
                text = page.get_text("text").strip()
                if len(text) > 20:
                    text_pages += 1

        if text_pages == page_count:
            return "digital"
        if text_pages == 0:
            return "scanned"
        return "mixed"

    def extract_text(self, pdf_path: str) -> dict[int, str]:
        if fitz is None:
            raise RuntimeError("PyMuPDF is not installed.")

        by_page: dict[int, str] = {}
        with fitz.open(pdf_path) as doc:
            for idx, page in enumerate(doc, start=1):
                by_page[idx] = page.get_text("text")
        return by_page

    def ocr_text(self, pdf_path: str, dpi: int | None = None) -> dict[int, str]:
        if fitz is None or pytesseract is None or Image is None:
            raise RuntimeError("OCR dependencies are not fully installed.")

        dpi_value = dpi or self.default_dpi
        by_page: dict[int, str] = {}

        with fitz.open(pdf_path) as doc:
            for idx, page in enumerate(doc, start=1):
                pix = page.get_pixmap(dpi=dpi_value)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                by_page[idx] = pytesseract.image_to_string(image, lang=self.ocr_lang)

        return by_page

    def extract_math_latex(self, pdf_path: str) -> list[dict]:
        # Placeholder. Plug pix2tex/Mathpix integration here.
        _ = pdf_path
        return []

    def merge_and_normalize(
        self,
        raw_text_by_page: dict[int, str],
        ocr_text_by_page: dict[int, str],
        latex_snippets: list[dict],
    ) -> str:
        merged_pages: list[str] = []
        page_numbers = sorted(set(raw_text_by_page) | set(ocr_text_by_page))

        for page in page_numbers:
            digital = raw_text_by_page.get(page, "").strip()
            scanned = ocr_text_by_page.get(page, "").strip()
            merged = digital if len(digital) >= len(scanned) else scanned
            if merged:
                merged_pages.append(merged)

        latex_lines = [item.get("latex", "") for item in latex_snippets if item.get("latex")]
        merged_text = "\n".join(merged_pages + latex_lines)

        normalized = re.sub(r"[ \t]+", " ", merged_text)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def as_langchain_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                func=self.detect_pdf_type,
                name="detect_pdf_type",
                description="Detect whether a PDF is digital, scanned, or mixed.",
            ),
            StructuredTool.from_function(
                func=self.extract_text,
                name="extract_text_from_pdf",
                description="Extract digital text from a PDF by page.",
            ),
            StructuredTool.from_function(
                func=self.ocr_text,
                name="ocr_text_from_pdf",
                description="Run OCR on PDF pages and return text by page.",
            ),
            StructuredTool.from_function(
                func=self.extract_math_latex,
                name="extract_math_latex",
                description="Extract equation snippets as LaTeX (placeholder).",
            ),
        ]
