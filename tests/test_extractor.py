import io

import pytest
from docx import Document
from reportlab.pdfgen import canvas

from resume_screener.extractor import UnsupportedFileError, extract_text_from_bytes


def make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf)
    y = 800
    for line in text.splitlines():
        pdf.drawString(72, y, line)
        y -= 18
    pdf.save()
    return buf.getvalue()


def make_docx(text: str) -> bytes:
    buf = io.BytesIO()
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(buf)
    return buf.getvalue()


def test_txt():
    assert extract_text_from_bytes(b"Hello   Python\n\n\nFlask", "cv.txt") == "Hello Python\nFlask"


def test_pdf():
    text = extract_text_from_bytes(make_pdf("Asha Rao\nSkills: Python, Flask"), "cv.pdf")
    assert "Asha Rao" in text and "Flask" in text


def test_docx():
    text = extract_text_from_bytes(make_docx("Asha Rao\nSkills: Django, MySQL"), "cv.docx")
    assert "Django" in text and "MySQL" in text


def test_unsupported():
    with pytest.raises(UnsupportedFileError):
        extract_text_from_bytes(b"x", "photo.png")
