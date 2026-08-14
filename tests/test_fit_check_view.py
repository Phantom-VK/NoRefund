"""Smoke tests for FitCheckView: recalculation, auto-fill, edge cases.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

ctk = pytest.importorskip("customtkinter")

from norefund.gui.fit_check_view import FitCheckView  # noqa: E402

from .conftest import _pump  # noqa: E402


@dataclass
class _FakeShell:
    last_analysis_tokens: int | None = None


def test_builds_and_fits_by_default(root):
    view = FitCheckView(root, _FakeShell())
    view.pack(fill="both", expand=True)
    _pump(root, 30)

    assert view._verdict_text.cget("text") == "Fits on this hardware"


def test_zero_context_renders_error_state(root):
    view = FitCheckView(root, _FakeShell())
    view.pack(fill="both", expand=True)
    view._context_var.set("0")
    view._recalculate()
    _pump(root, 30)

    assert view._verdict_text.cget("text") == "Can't estimate"
    assert "greater than zero" in view._error_label.cget("text")


def test_undersized_hardware_does_not_fit(root):
    view = FitCheckView(root, _FakeShell())
    view.pack(fill="both", expand=True)

    view._model_dropdown.select("meta:llama-3.1-405b")
    view._hw_dropdown.select("nvidia:rtx-3090-24gb")
    view._recalculate()
    _pump(root, 30)

    assert view._verdict_text.cget("text") == "Does not fit"
    assert "over" in view._headroom_pill._value_label.cget("text")


def test_on_show_autofills_context_when_not_user_edited(root):
    shell = _FakeShell(last_analysis_tokens=None)
    view = FitCheckView(root, shell)
    view.pack(fill="both", expand=True)
    assert view._context_var.get() == "8192"

    shell.last_analysis_tokens = 50_000
    view.on_show()
    _pump(root, 30)

    assert view._context_var.get() == "50000"


def test_on_show_does_not_clobber_manual_context_edit(root):
    shell = _FakeShell(last_analysis_tokens=None)
    view = FitCheckView(root, shell)
    view.pack(fill="both", expand=True)

    view._context_var.set("12345")
    view._on_context_edited()

    shell.last_analysis_tokens = 999_999
    view.on_show()
    _pump(root, 30)

    assert view._context_var.get() == "12345"
