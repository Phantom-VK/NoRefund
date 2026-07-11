from __future__ import annotations

from norefund.core.compare import CompareReport, ModelComparison
from norefund.core.export import (
    analysis_results_to_csv,
    analysis_results_to_markdown,
    comparison_to_csv,
    comparison_to_markdown,
)
from norefund.core.models_registry import ModelInfo
from norefund.core.service import AnalysisResult


def _model() -> ModelInfo:
    return ModelInfo(
        id="test:model",
        display_name="Test Model",
        provider="Test",
        tokenizer_backend="tiktoken",
        tokenizer_name="cl100k_base",
        context_window=1000,
        input_price_per_million=1.0,
        output_price_per_million=2.0,
    )


def _comparison(**overrides) -> ModelComparison:
    defaults = dict(
        model=_model(),
        token_count=100,
        context_usage_pct=10.0,
        fits_in_context=True,
        min_chunks_needed=1,
        output_tokens=50,
        input_cost=0.0001,
        output_cost=0.0001,
        total_cost=0.0002,
        tokenizer_is_approximate=False,
        error=None,
    )
    defaults.update(overrides)
    return ModelComparison(**defaults)


def test_comparison_to_csv_has_header_and_row():
    report = CompareReport(source_label="test", results=[_comparison()])
    csv_text = comparison_to_csv(report)
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("Model,Provider,Tokens")
    assert "Test Model" in lines[1]


def test_comparison_to_csv_marks_approximate_tokens():
    report = CompareReport(
        source_label="test", results=[_comparison(tokenizer_is_approximate=True)]
    )
    csv_text = comparison_to_csv(report)
    assert "~100" in csv_text


def test_comparison_to_csv_empty_results():
    report = CompareReport(source_label="empty", results=[])
    csv_text = comparison_to_csv(report)
    assert csv_text.strip().splitlines() == [
        "Model,Provider,Tokens,Context %,Fits,Chunks,Input Cost,Output Cost,Total Cost,Error"
    ]


def test_comparison_to_markdown_includes_source_label_and_approx_marker():
    report = CompareReport(
        source_label="my-doc.pdf", results=[_comparison(tokenizer_is_approximate=True)]
    )
    md = comparison_to_markdown(report)
    assert "my-doc.pdf" in md
    assert "~100" in md


def test_comparison_to_markdown_empty_results():
    report = CompareReport(source_label="empty", results=[])
    md = comparison_to_markdown(report)
    assert "No results." in md


def test_comparison_to_markdown_shows_error_row():
    report = CompareReport(
        source_label="test", results=[_comparison(error="Tokenizer unavailable")]
    )
    md = comparison_to_markdown(report)
    assert "error: Tokenizer unavailable" in md


def _analysis_result(**overrides) -> AnalysisResult:
    defaults = dict(
        file_path="doc.pdf",
        model_id="test:model",
        char_count=1000,
        word_count=200,
        token_count=250,
        context_window=1000,
        context_usage_pct=25.0,
        fits_in_context=True,
        min_chunks_needed=1,
        estimated_input_cost=0.0005,
        error=None,
    )
    defaults.update(overrides)
    return AnalysisResult(**defaults)


def test_analysis_results_to_csv_has_header_and_row():
    csv_text = analysis_results_to_csv([_analysis_result()])
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("File,Model,Tokens")
    assert "doc.pdf" in lines[1]


def test_analysis_results_to_csv_empty():
    csv_text = analysis_results_to_csv([])
    assert len(csv_text.strip().splitlines()) == 1


def test_analysis_results_to_markdown_shows_error_row():
    md = analysis_results_to_markdown([_analysis_result(error="parse failed")])
    assert "error: parse failed" in md


def test_analysis_results_to_markdown_empty():
    md = analysis_results_to_markdown([])
    assert "No results." in md
