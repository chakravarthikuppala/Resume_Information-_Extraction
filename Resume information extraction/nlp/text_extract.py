"""Step 2: extract raw text from uploaded resume files."""

from __future__ import annotations

from pathlib import Path
from zipfile import BadZipFile

import pdfplumber
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from pdfplumber.utils.exceptions import PdfminerException


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def extract_text(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _from_pdf(path)
    if suffix == ".docx":
        return _from_docx(path)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix}. Use PDF, DOCX, or TXT.")


def _from_pdf(path: Path) -> str:
    pages = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    use_text_flow=True,
                    keep_blank_chars=False,
                )
                if words:
                    lines = []
                    current_top = None
                    current_words = []
                    for word in words:
                        top = round(word["top"], 1)
                        if current_top is None or abs(top - current_top) <= 2:
                            current_words.append(word)
                            current_top = top if current_top is None else (current_top + top) / 2
                        else:
                            lines.append(_join_pdf_words(current_words))
                            current_words = [word]
                            current_top = top
                    if current_words:
                        lines.append(_join_pdf_words(current_words))
                    pages.append("\n".join(lines))
                else:
                    pages.append(page.extract_text() or "")
    except (PdfminerException, OSError) as exc:
        raise ValueError("The PDF could not be read. Upload a valid, unencrypted PDF.") from exc
    return "\n".join(pages).strip()


def _join_pdf_words(words: list[dict]) -> str:
    if not words:
        return ""
    ordered = sorted(words, key=lambda item: (item["x0"], item["top"]))
    parts = [str(ordered[0]["text"])]
    for previous, current in zip(ordered, ordered[1:]):
        gap = float(current["x0"]) - float(previous["x1"])
        parts.append((" " if gap > 1.5 else "") + str(current["text"]))
    return "".join(parts)


def _from_docx(path: Path) -> str:
    try:
        document = Document(path)
    except (PackageNotFoundError, BadZipFile, OSError) as exc:
        raise ValueError("The DOCX could not be read. Upload a valid DOCX document.") from exc
    parts = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts).strip()
