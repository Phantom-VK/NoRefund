"""Shared pytest fixtures/helpers.

Also mirrors main.py's _init_tiktoken_cache_dir(): pytest never imports
norefund.main, so without this tiktoken falls back to its own tempdir
cache instead of the app's persistent one, making every tokenizer
"uncached" even when it's already been downloaded.
"""

from __future__ import annotations

import os
import time

import pytest

from norefund.core.paths import tiktoken_cache_dir

os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(tiktoken_cache_dir()))


def _skip_unless_cached(encoding_name: str) -> None:
    """Skip (not fail) when the real vocab file isn't cached on this machine.

    NoRefund never downloads tiktoken vocab files on its own -- only the
    Resources view's Download button does that -- so a machine that has
    never opened it (e.g. a fresh CI runner) won't have it cached. Tests
    that need real cached vocab bytes call this first instead of assuming
    the encoding is present.
    """
    from norefund.core.resources import probe_tiktoken

    if not probe_tiktoken(encoding_name).is_cached:
        pytest.skip(
            f"'{encoding_name}' not cached locally — open Resources in the "
            "app (or run the CLI hint in TikTokenOfflineError) to cache it"
        )


@pytest.fixture
def root():
    ctk = pytest.importorskip("customtkinter")
    try:
        r = ctk.CTk()
        r.withdraw()
    except Exception as exc:  # no display available
        pytest.skip(f"no Tk display available: {exc}")
    yield r
    r.destroy()


def _pump(root, ms: int) -> None:
    """Run a real Tcl mainloop for `ms` milliseconds.

    Views that do work on a background threading.Thread (Resources,
    Compare) call back into Tk via self.after(0, ...) from that other
    thread. Tcl only allows cross-thread calls while the main thread is
    actually inside mainloop() -- polling with plain root.update() calls
    leaves it "not in the main loop" and those callbacks raise
    RuntimeError. A real mainloop, stopped with quit(), doesn't have that
    restriction.
    """
    root.after(ms, root.quit)
    root.mainloop()


def _pump_until(root, predicate, timeout_ms: int = 3000) -> None:
    deadline = time.monotonic() + timeout_ms / 1000

    def _check() -> None:
        if predicate() or time.monotonic() >= deadline:
            root.quit()
        else:
            root.after(20, _check)

    root.after(0, _check)
    root.mainloop()
    if not predicate():
        pytest.fail("condition not met within timeout")
