"""Window creation and lifecycle for the NoRefund desktop app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from norefund.core.paths import tiktoken_cache_dir

# Point tiktoken at a persistent cache dir before it's imported anywhere --
# it otherwise defaults to a tempdir the OS can wipe, which would make a
# tokenizer downloaded via the Resources view "not downloaded" again on the
# next run. main.py (the legacy Tk entrypoint) does this same thing at
# import time; this is the equivalent for the desktop entrypoint, since
# nothing here imports main.py.
if "TIKTOKEN_CACHE_DIR" not in os.environ:
    os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_cache_dir())

import webview  # noqa: E402

from norefund.core.paths import bundled_resource  # noqa: E402
from norefund.desktop.api import Api  # noqa: E402

DEV_SERVER_URL = "http://localhost:5173"
WINDOW_TITLE = "NoRefund — Token & Cost Analyzer"

PREFERRED_WIDTH = 1440
PREFERRED_HEIGHT = 900
MIN_WIDTH = 1024
MIN_HEIGHT = 640
# Room for a taskbar/dock/menu bar so the window never opens taller than the
# usable area of a 768px-high panel.
_CHROME_MARGIN = 40


def _web_dir() -> Path:
    """Built frontend assets, resolved the same way in dev and frozen builds."""
    return bundled_resource("web")


WEB_DIR: Path = _web_dir()


def resolve_entrypoint() -> str | Path:
    """The dev server when NOREFUND_DEV=1, otherwise the built index.html."""
    if os.environ.get("NOREFUND_DEV") == "1":
        return DEV_SERVER_URL
    index = WEB_DIR / "index.html"
    if not index.exists():
        raise RuntimeError(
            f"Frontend build not found at {index}. "
            f"Run: cd frontend && npm install && npm run build"
        )
    return index


def preferred_gui() -> str | None:
    """Explicit renderer per platform.

    Left to pywebview's own detection on macOS (WebKit is the only option).
    Pinned elsewhere so an unrelated Qt or CEF install on the build machine
    cannot silently change which engine ships.
    """
    if sys.platform.startswith("linux"):
        return "gtk"
    if sys.platform == "win32":
        return "edgechromium"
    return None


def missing_runtime_message() -> str | None:
    """A user-facing install hint if this machine lacks the system webview."""
    if sys.platform.startswith("linux"):
        try:
            import gi

            gi.require_version("WebKit2", "4.1")
        except (ImportError, ValueError):
            return (
                "NoRefund needs the WebKitGTK runtime, which is missing.\n\n"
                "Install it with:\n"
                "  Debian/Ubuntu:  sudo apt install "
                "python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1\n"
                "  Fedora:         sudo dnf install python3-gobject webkit2gtk4.1\n"
                "  Arch:           sudo pacman -S python-gobject webkit2gtk-4.1"
            )
    if sys.platform == "win32":
        try:
            import clr  # noqa: F401
        except ImportError:
            return (
                "NoRefund needs the Microsoft Edge WebView2 runtime.\n\n"
                "Download it from:\n"
                "  https://developer.microsoft.com/microsoft-edge/webview2/"
            )
    return None


def initial_window_size(screen_width: int, screen_height: int) -> tuple[int, int]:
    """Preferred size, clamped so the window always fits the actual display."""
    width = max(MIN_WIDTH, min(PREFERRED_WIDTH, screen_width))
    height = max(MIN_HEIGHT, min(PREFERRED_HEIGHT, screen_height - _CHROME_MARGIN))
    return width, height


def create_app_window(js_api: object | None = None) -> webview.Window:
    """Create the single application window. Phase 03 passes a real js_api."""
    screens = webview.screens
    if screens:
        width, height = initial_window_size(screens[0].width, screens[0].height)
    else:
        width, height = PREFERRED_WIDTH, PREFERRED_HEIGHT
    return webview.create_window(
        WINDOW_TITLE,
        str(resolve_entrypoint()),
        js_api=js_api,
        width=width,
        height=height,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
        background_color="#111318",  # matches --background dark; avoids a white flash
        text_select=False,
        confirm_close=False,
    )


def main() -> None:
    problem = missing_runtime_message()
    if problem is not None:
        print(problem, file=sys.stderr)
        raise SystemExit(2)
    api = Api()
    window = create_app_window(js_api=api)
    api.bind_window(window)
    webview.start(
        gui=preferred_gui(),
        debug=os.environ.get("NOREFUND_DEV") == "1",
    )


if __name__ == "__main__":
    main()
