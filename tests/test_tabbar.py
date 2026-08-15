"""Tests for the shared TabBar widget (used by Parser and Compare).

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import pytest

ctk = pytest.importorskip("customtkinter")

from norefund.gui.theme import COLORS  # noqa: E402
from norefund.gui.widgets import TabBar  # noqa: E402

from .conftest import _pump  # noqa: E402


def test_active_tab_starts_highlighted(root):
    tab_bar = TabBar(
        root, [("a", "Alpha"), ("b", "Bravo")], "a", on_change=lambda _t: None
    )
    tab_bar.pack()
    _pump(root, 20)

    assert tab_bar._buttons["a"].cget("text_color") == COLORS["primary"]
    assert tab_bar._buttons["b"].cget("text_color") == COLORS["muted_fg"]


def test_clicking_a_tab_restyles_and_notifies(root):
    calls: list[str] = []
    tab_bar = TabBar(
        root, [("a", "Alpha"), ("b", "Bravo")], "a", on_change=calls.append
    )
    tab_bar.pack()
    _pump(root, 20)

    tab_bar._buttons["b"].invoke()
    _pump(root, 20)

    assert calls == ["b"]
    assert tab_bar._buttons["b"].cget("text_color") == COLORS["primary"]
    assert tab_bar._buttons["a"].cget("text_color") == COLORS["muted_fg"]
