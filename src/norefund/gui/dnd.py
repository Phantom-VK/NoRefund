"""Optional drag-and-drop support, built on the optional `tkinterdnd2` dep.

Every entry point degrades to a no-op when the library isn't installed, so
the app works identically with or without it.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _AVAILABLE = True
except ImportError:
    DND_FILES = None
    TkinterDnD = None
    _AVAILABLE = False


def dnd_available() -> bool:
    return _AVAILABLE


def dnd_root_class():
    """Return the Tk root mixin class to use, or None if unavailable."""
    return TkinterDnD.Tk if _AVAILABLE else None


def parse_dropped_paths(data: str) -> list[Path]:
    """Parse a Tcl brace-quoted list of paths, as delivered by tkinterdnd2.

    Paths containing spaces are wrapped in {}; others are bare and
    whitespace-separated.
    """
    tokens = re.findall(r"\{[^}]*\}|\S+", data.strip())
    return [Path(t.strip("{}")) for t in tokens]


def enable_file_drop(
    widget, on_paths: Callable[[list[Path]], None], *, suffixes: set[str] | None = None
) -> bool:
    """Register `widget` as a file drop target. Returns False (no-op) if
    tkinterdnd2 isn't installed."""
    if not _AVAILABLE:
        return False

    def _on_drop(event) -> None:
        paths = parse_dropped_paths(event.data)
        if suffixes is not None:
            paths = [p for p in paths if p.is_dir() or p.suffix.lower() in suffixes]
        if paths:
            on_paths(paths)

    widget.drop_target_register(DND_FILES)
    widget.dnd_bind("<<Drop>>", _on_drop)
    return True
