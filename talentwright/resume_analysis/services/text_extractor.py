"""Multi-format resume text extraction service.

Supports extracting clean textual content from:
- PDF (.pdf) using PyMuPDF (fitz)
- Word Documents (.docx) using built-in ZIP/XML extraction or python-docx
- Plain Text (.txt)
"""

from __future__ import annotations

import io
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import BinaryIO

import fitz  # PyMuPDF

from talentwright.resume_analysis.exceptions import EmptyResumeError
from talentwright.resume_analysis.exceptions import TextExtractionError
from talentwright.resume_analysis.exceptions import UnsupportedFileFormatError

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text_from_file(
    file_source: str | Path | BinaryIO | bytes,
    filename: str | None = None,
) -> str:
    """Extract and normalize text content from an arbitrary resume file.

    Args:
        file_source: Path to file, open file-like binary stream, or raw bytes.
        filename: Optional filename hint to determine format when source is stream/bytes.

    Returns:
        Cleaned, normalized text content extracted from the resume.

    Raises:
        UnsupportedFileFormatError: If file extension is not supported.
        TextExtractionError: If extraction fails due to corruption or format errors.
        EmptyResumeError: If extracted content is empty or contains no text.
    """
    ext = _resolve_extension(file_source, filename)

    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileFormatError(
            f"Unsupported resume file format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    file_bytes = _read_to_bytes(file_source)
    if not file_bytes:
        raise EmptyResumeError("Resume file is empty (0 bytes).")

    try:
        if ext == ".pdf":
            raw_text = _extract_from_pdf(file_bytes)
        elif ext == ".docx":
            raw_text = _extract_from_docx(file_bytes)
        elif ext == ".txt":
            raw_text = _extract_from_txt(file_bytes)
        else:
            raise UnsupportedFileFormatError(
                f"Handler not implemented for extension: {ext}"
            )
    except UnsupportedFileFormatError, EmptyResumeError:
        raise
    except Exception as exc:
        logger.exception("Text extraction failed for file '%s' (%s)", filename, ext)
        raise TextExtractionError(
            f"Failed to extract text from {ext} file: {exc}"
        ) from exc

    cleaned_text = _clean_text(raw_text)
    if not cleaned_text or len(cleaned_text.strip()) < 10:
        raise EmptyResumeError(
            "Extracted resume content contains no legible text. The file may be an image-only scan or corrupted.",
        )

    return cleaned_text


def _resolve_extension(
    file_source: str | Path | BinaryIO | bytes, filename: str | None
) -> str:
    """Determine the file extension from filename or file path."""
    target_name = ""
    if filename:
        target_name = filename
    elif isinstance(file_source, (str, Path)):
        target_name = str(file_source)
    elif hasattr(file_source, "name") and isinstance(file_source.name, str):
        target_name = file_source.name

    ext = Path(target_name).suffix.lower()
    return ext


def _read_to_bytes(file_source: str | Path | BinaryIO | bytes) -> bytes:
    """Read any file source into raw bytes."""
    if isinstance(file_source, bytes):
        return file_source
    if isinstance(file_source, (str, Path)):
        return Path(file_source).read_bytes()
    if hasattr(file_source, "read"):
        if hasattr(file_source, "seek"):
            file_source.seek(0)
        content = file_source.read()
        return content if isinstance(content, bytes) else content.encode("utf-8")
    raise ValueError(f"Cannot read file source of type {type(file_source)}")


def _extract_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF using PyMuPDF."""
    doc = None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text: list[str] = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if text:
                pages_text.append(text)
        return "\n\n".join(pages_text)
    finally:
        if doc:
            doc.close()


def _extract_from_docx(docx_bytes: bytes) -> str:
    """Extract text from Word Document (.docx) via document.xml without heavy external dependencies."""
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            xml_content = z.read("word/document.xml")
    except Exception as exc:
        raise TextExtractionError(f"Corrupted or invalid DOCX archive: {exc}") from exc

    try:
        tree = ET.fromstring(xml_content)
        # WordProcessingML namespace
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []

        # Find all paragraph tags <w:p>
        for p in tree.iterfind(".//w:p", ns):
            text_pieces = [node.text for node in p.iterfind(".//w:t", ns) if node.text]
            if text_pieces:
                paragraphs.append("".join(text_pieces))

        return "\n\n".join(paragraphs)
    except Exception as exc:
        raise TextExtractionError(f"Failed parsing DOCX XML tree: {exc}") from exc


def _extract_from_txt(txt_bytes: bytes) -> str:
    """Extract text from raw text bytes handling common encodings."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return txt_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return txt_bytes.decode("utf-8", errors="replace")


def _clean_text(text: str) -> str:
    """Normalize whitespace, remove null bytes and extraneous blank lines."""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace multiple spaces with a single space
    text = re.sub(r"[ \t]+", " ", text)
    # Replace 3 or more consecutive newlines with 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
