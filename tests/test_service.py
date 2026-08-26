"""Tests for service orchestration."""

from pathlib import Path

import pytest

from norefund.core.service import AnalysisResult, analyze_file, analyze_folder

from .conftest import _skip_unless_cached


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    f = tmp_path / "sample.txt"
    f.write_text("Hello from NoRefund. This is a test document with some words.")
    return f


@pytest.fixture
def sample_folder(tmp_path: Path) -> Path:
    (tmp_path / "a.txt").write_text("File A content")
    (tmp_path / "b.md").write_text("# File B\nSome markdown content")
    (tmp_path / "ignore.exe").write_text("should be ignored")
    return tmp_path


def test_analyze_file_returns_result(sample_txt: Path):
    result = analyze_file(sample_txt, "openai:gpt-5.6-sol")
    assert isinstance(result, AnalysisResult)


def test_analyze_file_token_count_positive(sample_txt: Path):
    _skip_unless_cached("o200k_base")
    result = analyze_file(sample_txt, "openai:gpt-5.6-sol")
    assert result.token_count > 0


def test_analyze_file_correct_model(sample_txt: Path):
    result = analyze_file(sample_txt, "openai:gpt-5.6-sol")
    assert result.model_id == "openai:gpt-5.6-sol"


def test_analyze_file_fits_small_doc(sample_txt: Path):
    # A tiny txt file must fit in any model's context window
    _skip_unless_cached("o200k_base")
    result = analyze_file(sample_txt, "openai:gpt-5.6-sol")
    assert result.fits_in_context is True
    assert result.min_chunks_needed == 1


def test_analyze_file_context_usage_under_100(sample_txt: Path):
    _skip_unless_cached("o200k_base")
    result = analyze_file(sample_txt, "openai:gpt-5.6-sol")
    assert result.context_usage_pct < 100


def test_analyze_file_char_and_word_count(sample_txt: Path):
    _skip_unless_cached("o200k_base")
    result = analyze_file(sample_txt, "openai:gpt-5.6-sol")
    assert result.char_count > 0
    assert result.word_count > 0


def test_analyze_folder_returns_list(sample_folder: Path):
    results = analyze_folder(sample_folder, "openai:gpt-5.6-sol")
    assert isinstance(results, list)


def test_analyze_folder_ignores_unsupported(sample_folder: Path):
    results = analyze_folder(sample_folder, "openai:gpt-5.6-sol")
    # Only .txt and .md should be picked up, not .exe
    assert len(results) == 2


def test_analyze_folder_all_results_valid(sample_folder: Path):
    results = analyze_folder(sample_folder, "openai:gpt-5.6-sol")
    assert all(isinstance(r, AnalysisResult) for r in results)


def test_analyze_folder_does_not_descend_into_subfolders(sample_folder: Path):
    nested = sample_folder / "nested"
    nested.mkdir()
    (nested / "c.txt").write_text("File C content, inside a subfolder")

    results = analyze_folder(sample_folder, "openai:gpt-5.6-sol")

    assert {Path(r.file_path).name for r in results} == {"a.txt", "b.md"}
