"""Smoke tests for ParserView's report export (PDF + HTML).

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

ctk = pytest.importorskip("customtkinter")

import norefund.gui.native_dialog as native_dialog_module  # noqa: E402
from norefund.core.models_registry import ModelInfo  # noqa: E402
from norefund.core.service import AnalysisResult  # noqa: E402
from norefund.core.settings import Settings  # noqa: E402
from norefund.gui.parser_view import ParserView  # noqa: E402

from .conftest import _pump  # noqa: E402


@dataclass
class _FakeShell:
    models: list
    settings: Settings

    def update_header_count(self, _count: int) -> None:
        pass

    def update_last_analysis_tokens(self, _tokens: int) -> None:
        pass


def _model() -> ModelInfo:
    return ModelInfo(
        id="test:only",
        display_name="Test Model",
        provider="Test",
        tokenizer_backend="tiktoken",
        tokenizer_name="cl100k_base",
        context_window=8000,
        input_price_per_million=1.0,
        output_price_per_million=1.0,
    )


def _result(model: ModelInfo) -> AnalysisResult:
    return AnalysisResult(
        file_path="doc.txt",
        model_id=model.id,
        char_count=100,
        word_count=20,
        token_count=30,
        context_window=model.context_window,
        context_usage_pct=0.4,
        fits_in_context=True,
        min_chunks_needed=1,
        estimated_input_cost=0.00003,
    )


def test_export_pdf_and_html_write_expected_content(root, monkeypatch, tmp_path):
    model = _model()
    view = ParserView(root, _FakeShell(models=[model], settings=Settings()))
    view.pack(fill="both", expand=True)
    _pump(root, 30)

    view._results = [_result(model)]

    pdf_path = tmp_path / "out.pdf"
    monkeypatch.setattr(
        native_dialog_module, "ask_save_file", lambda **kwargs: str(pdf_path)
    )
    view._export_pdf()
    assert pdf_path.read_bytes().startswith(b"%PDF")

    html_path = tmp_path / "out.html"
    monkeypatch.setattr(
        native_dialog_module, "ask_save_file", lambda **kwargs: str(html_path)
    )
    view._export_html()
    html = html_path.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "doc.txt" in html


def test_export_is_noop_with_no_results(root, monkeypatch, tmp_path):
    model = _model()
    view = ParserView(root, _FakeShell(models=[model], settings=Settings()))
    view.pack(fill="both", expand=True)
    _pump(root, 30)

    pdf_path = tmp_path / "out.pdf"
    monkeypatch.setattr(
        native_dialog_module, "ask_save_file", lambda **kwargs: str(pdf_path)
    )
    view._export_pdf()
    assert not pdf_path.exists()
