"""Read plain text out of PDF, DOCX and TXT resumes."""

from __future__ import annotations

import io
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class UnsupportedFileError(ValueError):
    """Raised when a resume has a file type we cannot read."""


def _clean(text: str) -> str:
    """Collapse extra spaces and blank lines so every format looks the same."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_text_from_bytes(data: bytes, filename: str) -> str:
    """Return the text inside an uploaded file, based on its extension."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"'{filename}' is not supported. Use PDF, DOCX or TXT."
        )

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        document = Document(io.BytesIO(data))
        parts = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append(" ".join(cell.text for cell in row.cells))
        text = "\n".join(parts)
    else:
        text = data.decode("utf-8", errors="ignore")

    return _clean(text)


def extract_text(path: str | Path) -> str:
    """Read a resume from disk (used by the command-line tool)."""
    path = Path(path)
    return extract_text_from_bytes(path.read_bytes(), path.name)
