"""PDF text extraction service.

Extracts raw text from PDF resume files using PyMuPDF (fitz).
Isolated so OCR or other document format support can be added later
without touching other pipeline stages.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pymupdf

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of a PDF text extraction attempt."""

    text: str | None = None
    page_count: int = 0
    success: bool = False
    error: str | None = None


def extract_text_from_pdf(file_field) -> ExtractionResult:
    """Extract text from a PDF file attached to a Django FileField.

    Reads file bytes via Django's storage API so it works with both
    local filesystem and remote (S3) storage backends.

    Args:
        file_field: A Django FieldFile instance (e.g. ``resume.file``).

    Returns:
        ExtractionResult with extracted text or error details.
    """
    # ── Read file bytes from storage ────────────────────────────────
    try:
        file_field.open("rb")
        file_bytes = file_field.read()
        file_field.close()
    except Exception:
        logger.exception("Failed to read resume file: %s", file_field.name)
        return ExtractionResult(
            error=f"Failed to read file: {file_field.name}",
        )

    # ── Open PDF with PyMuPDF ───────────────────────────────────────
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception:
        logger.exception("Failed to open PDF: %s", file_field.name)
        return ExtractionResult(
            error=f"Failed to open PDF: {file_field.name}",
        )

    # ── Extract text page-by-page ───────────────────────────────────
    try:
        page_count = len(doc)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()

        full_text = "\n".join(text_parts).strip()

        if not full_text:
            return ExtractionResult(
                page_count=page_count,
                error="PDF contains no extractable text",
            )

        logger.info(
            "Extracted %d characters from %d-page PDF: %s",
            len(full_text),
            page_count,
            file_field.name,
        )
        return ExtractionResult(
            text=full_text,
            page_count=page_count,
            success=True,
        )
    except Exception:
        logger.exception("Error extracting text from PDF: %s", file_field.name)
        try:
            doc.close()
        except Exception:  # noqa: BLE001
            pass
        return ExtractionResult(
            error=f"Error extracting text from PDF: {file_field.name}",
        )
