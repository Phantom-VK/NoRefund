"""Smoke tests for CompareView's run/what-if/export/cancel flows.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import pytest

ctk = pytest.importorskip("customtkinter")

import norefund.gui.compare_view as compare_view_module  # noqa: E402
import norefund.gui.native_dialog as native_dialog_module  # noqa: E402
from norefund.core.compare import CompareReport, ModelComparison  # noqa: E402
from norefund.core.export import comparison_to_csv, comparison_to_markdown  # noqa: E402
from norefund.core.models_registry import ModelInfo  # noqa: E402
from norefund.core.settings import Settings  # noqa: E402
from norefund.gui import theme  # noqa: E402
from norefund.gui.compare_view import CompareView  # noqa: E402
from norefund.gui.theme import COLORS  # noqa: E402

from .conftest import _pump, _pump_until  # noqa: E402


@dataclass
class _FakeShell:
    models: list
    settings: Settings


def _model(id_: str) -> ModelInfo:
    return ModelInfo(
        id=id_,
        display_name=id_,
        provider="Test",
        tokenizer_backend="tiktoken",
        tokenizer_name="cl100k_base",
        context_window=8000,
        input_price_per_million=1.0,
        output_price_per_million=1.0,
    )


def _comparison(
    model: ModelInfo,
    *,
    token_count=100,
    total_cost=0.01,
    error=None,
    fits_in_context=True,
) -> ModelComparison:
    return ModelComparison(
        model=model,
        token_count=token_count,
        context_usage_pct=1.0,
        fits_in_context=fits_in_context,
        min_chunks_needed=1,
        output_tokens=1024,
        input_cost=total_cost / 2,
        output_cost=total_cost / 2,
        total_cost=total_cost,
        tokenizer_is_approximate=False,
        error=error,
    )


def _shell(models: list[ModelInfo]) -> _FakeShell:
    return _FakeShell(models=models, settings=Settings())


def _label_texts(widget) -> list[str]:
    texts = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            texts.append(child.cget("text"))
        texts.extend(_label_texts(child))
    return texts


def _images(widget) -> list:
    images = []
    for child in widget.winfo_children():
        if isinstance(child, ctk.CTkLabel):
            img = child.cget("image")
            if img is not None:
                images.append(img)
        images.extend(_images(child))
    return images


def test_run_compare_renders_sorted_results_cheapest_highlighted(root, monkeypatch):
    cheap = _model("test:cheap")
    pricey = _model("test:pricey")
    report = CompareReport(
        source_label="12 characters",
        results=[
            _comparison(pricey, total_cost=0.05),
            _comparison(cheap, total_cost=0.01),
        ],
    )
    monkeypatch.setattr(
        compare_view_module, "compare_text", lambda text, models, output_tokens: report
    )

    view = CompareView(root, _shell([cheap, pricey]))
    view._text_box.insert("1.0", "hello world")
    view._run_compare()
    _pump_until(root, lambda: not view._running)

    cards = view._results_scroll.winfo_children()
    assert len(cards) == 2
    assert any("cheapest" in t for t in _label_texts(cards[0]))
    assert not any("cheapest" in t for t in _label_texts(cards[1]))


def test_cheapest_row_keeps_card_background_with_accent_strip(root, monkeypatch):
    # The cheapest row used to recolor the whole card COLORS["primary"],
    # which collided with primary_fg text/icons also defaulting to a
    # primary-ish color -- a left accent strip should signal "cheapest"
    # instead, with every card keeping the same neutral surface.
    cheap = _model("test:cheap")
    pricey = _model("test:pricey")
    report = CompareReport(
        source_label="x",
        results=[
            _comparison(pricey, total_cost=0.05),
            _comparison(cheap, total_cost=0.01),
        ],
    )
    monkeypatch.setattr(
        compare_view_module, "compare_text", lambda text, models, output_tokens: report
    )

    view = CompareView(root, _shell([cheap, pricey]))
    view._text_box.insert("1.0", "hello world")
    view._run_compare()
    _pump_until(root, lambda: not view._running)

    cheapest_card, other_card = view._results_scroll.winfo_children()
    assert cheapest_card.cget("fg_color") == COLORS["card"]
    assert other_card.cget("fg_color") == COLORS["card"]

    accent_strip = cheapest_card.winfo_children()[0]
    assert accent_strip.cget("fg_color") == COLORS["primary"]


def test_cheapest_row_fits_icon_stays_destructive_when_not_fitting(root, monkeypatch):
    cheap = _model("test:cheap")
    report = CompareReport(
        source_label="x",
        results=[_comparison(cheap, total_cost=0.01, fits_in_context=False)],
    )
    monkeypatch.setattr(
        compare_view_module, "compare_text", lambda text, models, output_tokens: report
    )

    view = CompareView(root, _shell([cheap]))
    view._text_box.insert("1.0", "hello world")
    view._run_compare()
    _pump_until(root, lambda: not view._running)

    card = view._results_scroll.winfo_children()[0]
    images = _images(card)
    destructive_icon = theme.icon_image(
        "x_circle", size=14, color=COLORS["destructive"]
    )
    muted_icon = theme.icon_image("x_circle", size=14, color=COLORS["muted_fg"])

    assert destructive_icon in images
    assert muted_icon not in images


def test_run_button_disabled_with_no_models_selected(root, monkeypatch):
    model = _model("test:only")
    view = CompareView(root, _shell([model]))

    assert view._check_list._on_change == view._sync_run_button_state
    assert view._run_btn.cget("state") == "normal"

    for var in view._check_list._vars.values():
        var.set(False)
    view._check_list._notify_change()
    assert view._run_btn.cget("state") == "disabled"

    for var in view._check_list._vars.values():
        var.set(True)
    view._check_list._notify_change()
    assert view._run_btn.cget("state") == "normal"


def test_output_tokens_entry_flags_invalid_input(root):
    model = _model("test:only")
    view = CompareView(root, _shell([model]))

    assert view._output_entry.cget("border_color") == COLORS["input_bg"]

    view._output_var.set("not a number")
    view._on_output_tokens_change()
    assert view._output_entry.cget("border_color") == COLORS["destructive"]

    view._output_var.set("2048")
    view._on_output_tokens_change()
    assert view._output_entry.cget("border_color") == COLORS["input_bg"]


def test_what_if_recomputes_without_recalling_compare_text(root, monkeypatch):
    model = _model("test:only")
    report = CompareReport(
        source_label="x", results=[_comparison(model, token_count=200, total_cost=0.02)]
    )
    calls: list[int] = []

    def fake_compare_text(text, models, output_tokens):
        calls.append(output_tokens)
        return report

    monkeypatch.setattr(compare_view_module, "compare_text", fake_compare_text)

    view = CompareView(root, _shell([model]))
    view._text_box.insert("1.0", "hello")
    view._run_compare()
    _pump_until(root, lambda: not view._running)
    assert calls == [1024]

    view._output_var.set("2048")
    view._on_output_tokens_change()
    _pump(root, 50)

    assert calls == [1024]
    assert view._report.results[0].output_tokens == 2048


def test_error_row_renders_message(root, monkeypatch):
    model = _model("test:broken")
    message = "Tokenizer unavailable — download it in Resources."
    report = CompareReport(
        source_label="x", results=[_comparison(model, error=message)]
    )
    monkeypatch.setattr(
        compare_view_module, "compare_text", lambda text, models, output_tokens: report
    )

    view = CompareView(root, _shell([model]))
    view._text_box.insert("1.0", "hello")
    view._run_compare()
    _pump_until(root, lambda: not view._running)

    cards = view._results_scroll.winfo_children()
    assert len(cards) == 1
    assert any(message in t for t in _label_texts(cards[0]))


def test_export_csv_and_md_write_expected_content(root, monkeypatch, tmp_path):
    model = _model("test:only")
    report = CompareReport(source_label="x", results=[_comparison(model)])
    monkeypatch.setattr(
        compare_view_module, "compare_text", lambda text, models, output_tokens: report
    )

    view = CompareView(root, _shell([model]))
    view._text_box.insert("1.0", "hello")
    view._run_compare()
    _pump_until(root, lambda: not view._running)

    csv_path = tmp_path / "out.csv"
    monkeypatch.setattr(
        native_dialog_module, "ask_save_file", lambda **kwargs: str(csv_path)
    )
    view._export_csv()
    with csv_path.open(encoding="utf-8", newline="") as f:
        assert f.read() == comparison_to_csv(view._report)

    md_path = tmp_path / "out.md"
    monkeypatch.setattr(
        native_dialog_module, "ask_save_file", lambda **kwargs: str(md_path)
    )
    view._export_md()
    assert md_path.read_text(encoding="utf-8") == comparison_to_markdown(view._report)

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
    assert model.display_name in html


def test_destroy_mid_run_does_not_crash(root, monkeypatch):
    model = _model("test:only")
    proceed = threading.Event()

    def slow_compare(text, models, output_tokens):
        proceed.wait(2)
        return CompareReport(source_label="x", results=[_comparison(model)])

    monkeypatch.setattr(compare_view_module, "compare_text", slow_compare)

    view = CompareView(root, _shell([model]))
    view._text_box.insert("1.0", "hello")
    view._run_compare()
    assert view._running is True
    view.destroy()
    proceed.set()
    _pump(root, 300)
