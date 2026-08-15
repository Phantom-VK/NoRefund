"""Two hand-rolled motion helpers — the app's entire animation surface.

CustomTkinter has no transition system (no transforms, no opacity, no
springs on Tk widgets), so both of these animate `fg_color`/`text_color`
directly via `after()` and `formatting.blend()`. Per Emil Kowalski's
frequency rule, nothing here touches view switching or hover (CTk already
handles hover) — only press feedback and the loading->loaded handoff.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from tkinter import TclError

from norefund.gui import formatting

_PRESS_FLOOR_MS = 90
_FADE_STEP_MS = 16


def _as_pair(color: str | tuple[str, str]) -> tuple[str, str]:
    if isinstance(color, str):
        return (color, color)
    return (color[0], color[1])


def _safe_configure(widget, **kwargs) -> None:
    try:
        if not widget.winfo_exists():
            return
        widget.configure(**kwargs)
    except (TclError, RuntimeError):
        pass


def press_feedback(button, *, alpha: float = 0.15) -> None:
    """Darken `button`'s fg_color on pointer-down, restore on release.

    Apple: respond on press, not release. For buttons with a transparent
    fg_color (e.g. sidebar rows) the tint is derived from hover_color
    instead, since there's no solid fg_color to darken. A short floor
    keeps fast clicks visually registering even when press and release
    land in the same event-loop tick.

    For a toggle/selection button (e.g. a filter pill), `command` runs as
    part of the same ButtonRelease-1 event, before this handler, and may
    recolor the button to reflect its new resting state (selected vs not).
    The scheduled restore only reverts fg_color if nothing has touched it
    since the press-darken was applied -- otherwise it would clobber the
    command's recolor a moment after it happens.
    """
    pressed_at = 0.0
    original_fg: str | tuple[str, str] | None = None
    pressed_fg: tuple[str, str] | None = None

    def _on_press(_event=None) -> None:
        nonlocal pressed_at, original_fg, pressed_fg
        fg = button.cget("fg_color")
        hover = button.cget("hover_color")
        reference = fg if fg not in (None, "transparent") else hover
        if reference in (None, "transparent"):
            original_fg = None
            return
        ref_light, ref_dark = _as_pair(reference)
        pressed_at = time.monotonic()
        original_fg = fg
        pressed_fg = (
            formatting.blend("#000000", ref_light, alpha),
            formatting.blend("#000000", ref_dark, alpha),
        )
        _safe_configure(button, fg_color=pressed_fg)

    def _on_release(_event=None) -> None:
        if original_fg is None:
            return
        elapsed_ms = (time.monotonic() - pressed_at) * 1000
        remaining = max(0, _PRESS_FLOOR_MS - int(elapsed_ms))

        def _restore() -> None:
            if not button.winfo_exists():
                return
            current = _as_pair(button.cget("fg_color"))
            if current == _as_pair(pressed_fg):
                _safe_configure(button, fg_color=original_fg)

        try:
            button.after(remaining, _restore)
        except (TclError, RuntimeError):
            pass

    button.bind("<Button-1>", _on_press, add="+")
    button.bind("<ButtonRelease-1>", _on_release, add="+")


def fade_text_color(
    widget,
    from_token: tuple[str, str],
    to_token: tuple[str, str],
    duration: int = 150,
    on_done: Callable[[], None] | None = None,
) -> None:
    """Interpolate `widget`'s text_color from `from_token` to `to_token`.

    Auto-cancels if `widget` is destroyed mid-fade so a stray `after()`
    callback can't fire against a dead widget.
    """
    steps = max(1, duration // _FADE_STEP_MS)
    cancelled = False

    def _cancel(_event=None) -> None:
        nonlocal cancelled
        cancelled = True

    widget.bind("<Destroy>", _cancel, add="+")

    def _step(i: int) -> None:
        if cancelled:
            return
        alpha = i / steps
        light = formatting.blend(to_token[0], from_token[0], alpha)
        dark = formatting.blend(to_token[1], from_token[1], alpha)
        _safe_configure(widget, text_color=(light, dark))
        if i >= steps:
            if on_done is not None:
                on_done()
            return
        try:
            widget.after(_FADE_STEP_MS, _step, i + 1)
        except (TclError, RuntimeError):
            pass

    _step(0)
