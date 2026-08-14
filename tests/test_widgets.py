"""Tests for the generic DropdownButton/DropdownPopover widget.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import pytest

ctk = pytest.importorskip("customtkinter")

from norefund.gui.theme import COLORS  # noqa: E402
from norefund.gui.widgets import DropdownButton, DropdownItem  # noqa: E402

from .conftest import _pump  # noqa: E402

_ITEMS = [
    DropdownItem(value="a", label="Alpha"),
    DropdownItem(value="b", label="Bravo"),
    DropdownItem(value="c", label="Charlie"),
]


def test_shows_initial_selected_label(root):
    button = DropdownButton(root, _ITEMS, "b", on_select=lambda _v: None)
    button.pack()
    _pump(root, 20)
    assert button._text_label.cget("text") == "Bravo"


def test_select_updates_display_without_firing_callback(root):
    calls: list[str] = []
    button = DropdownButton(root, _ITEMS, "a", on_select=calls.append)
    button.pack()

    button.select("c")

    assert button.selected_value() == "c"
    assert button._text_label.cget("text") == "Charlie"
    assert calls == []


def test_toggle_opens_popover_matching_trigger_width(root):
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.configure(width=300)
    button.pack()
    _pump(root, 20)

    button._toggle()
    _pump(root, 20)

    assert button._popover is not None
    assert button._popover.winfo_exists()
    popover_width = int(button._popover.geometry().split("x")[0])
    assert popover_width == max(button.winfo_width(), 220)

    button._popover.destroy()


def test_picking_a_row_fires_callback_updates_selection_and_closes(root):
    calls: list[str] = []
    button = DropdownButton(root, _ITEMS, "a", on_select=calls.append)
    button.pack()
    _pump(root, 20)

    button._toggle()
    _pump(root, 20)
    popover = button._popover
    popover._pick("c")
    _pump(root, 20)

    assert calls == ["c"]
    assert button.selected_value() == "c"
    assert not popover.winfo_exists()
    assert button._popover is None


def test_toggle_twice_closes_without_picking(root):
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    _pump(root, 20)

    button._toggle()
    _pump(root, 20)
    popover = button._popover
    button._toggle()
    _pump(root, 20)

    assert not popover.winfo_exists()
    assert button._popover is None


def test_hover_and_selected_row_colors(root):
    # CTkFrame.bind() redirects to its internal ._canvas -- real mouse
    # Enter/Leave lands there too, since the canvas fills the frame.
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    _pump(root, 20)
    button._toggle()
    _pump(root, 20)
    popover = button._popover

    selected_row = popover.rows["a"]
    other_row = popover.rows["b"]
    assert tuple(selected_row.cget("fg_color")) == COLORS["sidebar_accent"]
    assert other_row.cget("fg_color") == "transparent"

    other_row._canvas.event_generate("<Enter>")
    _pump(root, 20)
    assert tuple(other_row.cget("fg_color")) == COLORS["popover_hover"]

    other_row._canvas.event_generate("<Leave>")
    _pump(root, 20)
    assert other_row.cget("fg_color") == "transparent"

    # Hovering the selected row itself must not lose its selected tint.
    selected_row._canvas.event_generate("<Enter>")
    _pump(root, 20)
    assert tuple(selected_row.cget("fg_color")) == COLORS["popover_hover"]
    selected_row._canvas.event_generate("<Leave>")
    _pump(root, 20)
    assert tuple(selected_row.cget("fg_color")) == COLORS["sidebar_accent"]

    popover.destroy()


def test_popover_follows_window_on_resize(root):
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    root.geometry("500x400+0+0")
    _pump(root, 20)

    button._toggle()
    _pump(root, 20)
    popover = button._popover
    before = popover.geometry()

    root.geometry("900x700+50+50")
    _pump(root, 20)
    after = popover.geometry()

    assert after != before
    popover.destroy()


def test_close_all_closes_every_open_popover(root):
    b1 = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    b2 = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    b1.pack()
    b2.pack()
    _pump(root, 20)

    b1._toggle()
    b2._toggle()
    _pump(root, 20)
    assert b1._popover is not None
    assert b2._popover is not None

    DropdownButton.close_all()
    _pump(root, 20)

    assert b1._popover is None
    assert b2._popover is None
