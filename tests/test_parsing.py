"""Tests for parsing module."""

from pathlib import Path
from norefund.core.parsing import extract_text, SUPPORTED_EXTENSIONS


def test_supported_extensions_present():
    assert ".pdf" in SUPPORTED_EXTENSIONS
    assert ".pptx" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS
    assert ".txt" in SUPPORTED_EXTENSIONS


def test_extract_text_txt(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_text("Hello NoRefund")
    assert extract_text(f) == "Hello NoRefund"


def test_extract_text_md(tmp_path: Path):
    f = tmp_path / "note.md"
    f.write_text("# Title\nContent here")
    result = extract_text(f)
    assert "Title" in result
