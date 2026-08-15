"""Tests for the generic DropdownButton/DropdownPopover widget.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import pytest

ctk = pytest.importorskip("customtkinter")

from norefund.gui import theme  # noqa: E402
from norefund.gui.widgets import (  # noqa: E402
    DropdownButton,
    DropdownItem,
    _popover_geometry,
)

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
    # Rows are plain tk.Frame (not CTkFrame) for construction speed, so
    # bindings land directly on the row -- no internal-canvas indirection.
    is_dark = ctk.get_appearance_mode() == "Dark"
    resting = theme.resolve("popover", is_dark)
    selected_resting = theme.resolve("sidebar_accent", is_dark)
    hover = theme.resolve("popover_hover", is_dark)

    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    _pump(root, 20)
    button._toggle()
    _pump(root, 20)
    popover = button._popover

    selected_row = popover.rows["a"]
    other_row = popover.rows["b"]
    assert str(selected_row.cget("bg")) == selected_resting
    assert str(other_row.cget("bg")) == resting

    other_row.event_generate("<Enter>")
    _pump(root, 20)
    assert str(other_row.cget("bg")) == hover

    other_row.event_generate("<Leave>")
    _pump(root, 20)
    assert str(other_row.cget("bg")) == resting

    # Hovering the selected row itself must not lose its selected tint.
    selected_row.event_generate("<Enter>")
    _pump(root, 20)
    assert str(selected_row.cget("bg")) == hover
    selected_row.event_generate("<Leave>")
    _pump(root, 20)
    assert str(selected_row.cget("bg")) == selected_resting

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


def test_popover_matches_trigger_width_at_hidpi_scaling(root):
    # Regression: CTkToplevel.geometry() re-multiplies width/height (but not
    # x/y) by the window's scaling factor -- at scaling 1.0 that's a no-op,
    # which is why the plain width test above didn't catch this. Force a
    # HiDPI-like scaling factor and confirm the popover still renders at the
    # trigger's real device-pixel width, not scaled again on top of it.
    ctk.ScalingTracker.set_widget_scaling(1.5)
    ctk.ScalingTracker.set_window_scaling(1.5)
    try:
        button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
        button.configure(width=300)
        button.pack()
        _pump(root, 20)

        button._toggle()
        _pump(root, 30)

        expected = max(button.winfo_width(), 220)
        assert abs(button._popover.winfo_width() - expected) <= 1
        button._popover.destroy()
    finally:
        ctk.ScalingTracker.set_widget_scaling(1.0)
        ctk.ScalingTracker.set_window_scaling(1.0)
        _pump(root, 20)


def test_popover_geometry_flips_upward_near_bottom_of_screen(root, monkeypatch):
    # Drives _popover_geometry directly rather than through a real toggle:
    # under a WM-less Xvfb (no window manager to honor absolute placement
    # requests for a plain, non-override-redirect toplevel), `root`/`button`
    # winfo_rooty() stays pinned at 0 regardless of any geometry() call, so
    # a real end-to-end version of this test can't reliably force "anchor
    # near the bottom of the screen" -- monkeypatching the winfo methods
    # this function actually reads exercises the same decision directly.
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    _pump(root, 20)
    monkeypatch.setattr(button, "winfo_rooty", lambda: 900)
    monkeypatch.setattr(button, "winfo_screenheight", lambda: 1000)

    geometry = _popover_geometry(button, root, row_count=3, row_height=42)

    y = int(geometry.rsplit("+", 1)[-1])
    assert y < 900  # opened above the anchor, not below it off-screen


def test_unmap_closes_open_popovers(root):
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    _pump(root, 20)
    button._toggle()
    _pump(root, 20)
    assert button._popover is not None

    root.event_generate("<Unmap>")
    _pump(root, 20)

    assert button._popover is None


def test_focus_out_closes_open_popovers_when_app_loses_focus(root, monkeypatch):
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    _pump(root, 20)
    button._toggle()
    _pump(root, 20)
    assert button._popover is not None

    monkeypatch.setattr(root, "focus_get", lambda: None)
    root.event_generate("<FocusOut>")
    _pump(root, 20)

    assert button._popover is None


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


# Keyboard-navigation tests below need a *visible* (not withdrawn) root:
# real KeyPress dispatch follows actual X input focus, and under a
# window-manager-less Xvfb (this test environment), a withdrawn toplevel
# can never hold real focus, so focus_set() silently no-ops and no
# KeyPress ever arrives. A visible root's own focus_force() (bypassing
# WM cooperation entirely, since there's no WM here to cooperate with)
# does work, which is what these use instead of the shared `root` fixture.
@pytest.fixture
def visible_root():
    try:
        r = ctk.CTk()
    except Exception as exc:  # no display available
        pytest.skip(f"no Tk display available: {exc}")
    yield r
    r.destroy()


def test_return_and_space_open_the_dropdown(visible_root):
    root = visible_root
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    root.update()

    button._canvas.focus_force()
    root.update()
    button._canvas.event_generate("<Return>")
    root.update()

    assert button._popover is not None
    button._popover.destroy()
    root.update()

    button._canvas.event_generate("<space>")
    root.update()
    assert button._popover is not None


def test_focus_in_and_out_toggle_the_border_color(visible_root):
    root = visible_root
    button = DropdownButton(root, _ITEMS, "a", on_select=lambda _v: None)
    button.pack()
    root.update()
    rest_color = button.cget("border_color")

    button._canvas.focus_force()
    root.update()
    assert button.cget("border_color") == theme.COLORS["primary"]

    button._canvas.event_generate("<FocusOut>")
    root.update()
    assert button.cget("border_color") == rest_color


def test_arrow_keys_move_highlight_and_return_selects_and_closes(visible_root):
    root = visible_root
    picks: list[str] = []
    button = DropdownButton(root, _ITEMS, "a", on_select=picks.append)
    button.pack()
    root.update()

    button._canvas.focus_force()
    root.update()
    button._canvas.event_generate("<Return>")
    root.update()
    popover = button._popover
    assert popover is not None
    popover.focus_force()
    root.update()

    assert popover._highlighted == "a"
    popover.event_generate("<Down>")
    root.update()
    assert popover._highlighted == "b"
    popover.event_generate("<Down>")
    root.update()
    assert popover._highlighted == "c"
    popover.event_generate("<Up>")
    root.update()
    assert popover._highlighted == "b"

    popover.event_generate("<Return>")
    root.update()

    assert picks == ["b"]
    assert button.selected_value() == "b"
    assert button._popover is None
    # Focus returns to the trigger so Tab/Return keep working right after.
    assert root.focus_get() is button._canvas


def test_escape_closes_popover_without_selecting(visible_root):
    root = visible_root
    picks: list[str] = []
    button = DropdownButton(root, _ITEMS, "a", on_select=picks.append)
    button.pack()
    root.update()

    button._canvas.focus_force()
    root.update()
    button._canvas.event_generate("<Return>")
    root.update()
    popover = button._popover
    popover.focus_force()
    root.update()

    popover.event_generate("<Down>")
    root.update()
    popover.event_generate("<Escape>")
    root.update()

    assert picks == []
    assert button.selected_value() == "a"
    assert button._popover is None
