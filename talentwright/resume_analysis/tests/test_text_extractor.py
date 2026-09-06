"""Tests for resume text extraction service."""

import io
import zipfile

import fitz
import pytest

from talentwright.resume_analysis.exceptions import EmptyResumeError
from talentwright.resume_analysis.exceptions import TextExtractionError
from talentwright.resume_analysis.exceptions import UnsupportedFileFormatError
from talentwright.resume_analysis.services.text_extractor import extract_text_from_file


def _create_sample_pdf_bytes(
    text: str = "John Doe\nSoftware Engineer\nPython, Django, AWS",
) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _create_sample_docx_bytes(
    text: str = "Jane Smith\nDevOps Engineer\nDocker, Kubernetes",
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        xml_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>"""
        z.writestr("word/document.xml", xml_content)
    return buf.getvalue()


class TestTextExtractor:
    def test_extract_from_valid_pdf_bytes(self):
        pdf_bytes = _create_sample_pdf_bytes()
        text = extract_text_from_file(pdf_bytes, filename="resume.pdf")
        assert "John Doe" in text
        assert "Python, Django, AWS" in text

    def test_extract_from_valid_docx_bytes(self):
        docx_bytes = _create_sample_docx_bytes()
        text = extract_text_from_file(docx_bytes, filename="cv.docx")
        assert "Jane Smith" in text
        assert "Docker, Kubernetes" in text

    def test_extract_from_txt_bytes(self):
        txt_bytes = b"Alex Rivera\nFrontend Architect\nReact, TypeScript, CSS"
        text = extract_text_from_file(txt_bytes, filename="profile.txt")
        assert "Alex Rivera" in text
        assert "Frontend Architect" in text

    def test_unsupported_extension_raises_error(self):
        with pytest.raises(UnsupportedFileFormatError) as exc_info:
            extract_text_from_file(b"data", filename="resume.png")
        assert "Unsupported resume file format '.png'" in str(exc_info.value)

    def test_empty_file_raises_error(self):
        with pytest.raises(EmptyResumeError) as exc_info:
            extract_text_from_file(b"", filename="empty.pdf")
        assert "Resume file is empty" in str(exc_info.value)

    def test_corrupted_docx_raises_text_extraction_error(self):
        with pytest.raises(TextExtractionError):
            extract_text_from_file(b"not a real docx file", filename="broken.docx")

    def test_whitespace_and_newline_cleaning(self):
        raw = "Line 1   with   spaces\n\n\n\n\nLine 2\x00with null byte"
        txt_bytes = raw.encode("utf-8")
        text = extract_text_from_file(txt_bytes, filename="clean.txt")
        assert "\x00" not in text
        assert "Line 1 with spaces" in text
        assert "\n\n\n" not in text
