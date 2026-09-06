"""Tests for parsing module."""

from pathlib import Path

from norefund.core.parsing import SUPPORTED_EXTENSIONS, extract_text


def test_supported_code_extensions_present():
    expected = {
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".html",
        ".css",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".sql",
        ".sh",
        ".bash",
    }

    assert expected <= SUPPORTED_EXTENSIONS


def test_extract_text_txt(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_text("Hello NoRefund")
    assert extract_text(f) == "Hello NoRefund"


def test_extract_text_md(tmp_path: Path):
    f = tmp_path / "note.md"
    f.write_text("# Title\nContent here")
    result = extract_text(f)
    assert "Title" in result
