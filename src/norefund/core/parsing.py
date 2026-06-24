"""Extract plain text from supported document formats."""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".docx", ".txt", ".md", ".py", ".json"}


def extract_text(path: Path) -> str:
    """Dispatch to the right parser based on file extension."""
    ext = path.suffix.lower()
    parsers = {
        ".pdf": _read_pdf,
        ".pptx": _read_pptx,
        ".docx": _read_docx,
    }
    return parsers.get(ext, _read_text)(path)


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_pptx(path: Path) -> str:
    from pptx import Presentation

    prs = Presentation(path)
    texts = [
        shape.text
        for slide in prs.slides
        for shape in slide.shapes
        if shape.has_text_frame
    ]
    return "\n".join(texts)


def _read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(path)
    return "\n".join(para.text for para in doc.paragraphs)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")
