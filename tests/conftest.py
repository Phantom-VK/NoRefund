"""Shared pytest fixtures/helpers.

Also mirrors main.py's _init_tiktoken_cache_dir(): pytest never imports
norefund.main, so without this tiktoken falls back to its own tempdir
cache instead of the app's persistent one, making every tokenizer
"uncached" even when it's already been downloaded.
"""

from __future__ import annotations

import os

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
