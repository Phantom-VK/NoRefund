"""Smoke tests for ParserView's report export (PDF + HTML).

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

ctk = pytest.importorskip("customtkinter")

import norefund.gui.native_dialog as native_dialog_module  # noqa: E402
from norefund.core.models_registry import ModelInfo  # noqa: E402
from norefund.core.service import AnalysisResult  # noqa: E402
from norefund.core.settings import Settings  # noqa: E402
from norefund.gui.parser_view import LogsPanel, ParserView, ResultsTable  # noqa: E402
from norefund.gui.theme import COLORS  # noqa: E402

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


def test_row_hover_persists_across_child_widgets(root):
    # CTkFrame/CTkLabel redirect .bind() to an internal canvas, which
    # event_generate() does NOT do automatically -- synthetic events have
    # to target that canvas directly to reach the binding.
    table = ResultsTable(root)
    table.pack()
    table.set_results([_result(_model())])
    _pump(root, 20)

    row = table._row_frames[0]
    assert row.cget("fg_color") == "transparent"

    row._canvas.event_generate("<Enter>")
    _pump(root, 20)
    assert row.cget("fg_color") == COLORS["muted"]

    # Simulate the pointer moving from the row onto one of its own cell
    # widgets: Tk delivers <Leave> to the parent the instant this happens
    # (NotifyInferior) -- the highlight must not clear here, because the
    # child was bound too (not just the row frame).
    child = row.winfo_children()[1]
    child._canvas.event_generate("<Enter>")
    _pump(root, 20)
    assert row.cget("fg_color") == COLORS["muted"]

    row._canvas.event_generate("<Leave>")
    _pump(root, 20)
    assert row.cget("fg_color") == "transparent"


def test_add_paths_dedupes_by_resolved_path(root, tmp_path):
    model = _model()
    view = ParserView(root, _FakeShell(models=[model], settings=Settings()))
    view.pack(fill="both", expand=True)
    _pump(root, 30)

    f = tmp_path / "doc.txt"
    f.write_text("hello")

    view._add_paths([f])
    view._add_paths([f])
    view._add_paths([Path(str(f))])  # a different Path object, same file

    assert view._paths == [f]


def test_clear_shows_cleared_message_in_status_bar(root, tmp_path):
    model = _model()
    view = ParserView(root, _FakeShell(models=[model], settings=Settings()))
    view.pack(fill="both", expand=True)
    _pump(root, 30)

    f = tmp_path / "doc.txt"
    f.write_text("hello")
    view._add_paths([f])
    view._refresh_file_strip()

    view._clear()
    _pump(root, 20)

    assert "Cleared" in view._status_left.cget("text")
    assert "1" in view._status_left.cget("text")
    assert view._status_bar.winfo_manager() == "pack"


def test_clear_with_nothing_selected_does_not_show_status_bar(root):
    model = _model()
    view = ParserView(root, _FakeShell(models=[model], settings=Settings()))
    view.pack(fill="both", expand=True)
    _pump(root, 30)

    view._clear()
    _pump(root, 20)

    assert view._status_bar.winfo_manager() == ""


def test_logs_panel_refresh_reapplies_tag_colors_after_theme_toggle(root):
    panel = LogsPanel(root)
    panel.pack()
    _pump(root, 20)
    panel.refresh()
    _pump(root, 20)
    original = panel._textbox.tag_cget("ERROR", "foreground")
    was_dark = ctk.get_appearance_mode() == "Dark"

    try:
        ctk.set_appearance_mode("Light" if was_dark else "Dark")
        panel.refresh()
        _pump(root, 20)
        assert panel._textbox.tag_cget("ERROR", "foreground") != original
    finally:
        ctk.set_appearance_mode("Dark" if was_dark else "Light")
