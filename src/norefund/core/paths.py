"""Packaging-safe filesystem paths.

Centralizes every place NoRefund reads bundled resources or writes user
state, so the same code works from a source checkout and from a frozen
PyInstaller build (where bundled files live under `sys._MEIPASS` instead
of next to this module).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_log_dir

_APP_NAME = "NoRefund"
_APP_AUTHOR = "PhantomVK"


def bundled_resource(relpath: str) -> Path:
    """Resolve a read-only resource shipped inside the app (e.g. config YAML).

    In a source checkout this is `src/norefund/<relpath>`. In a frozen
    PyInstaller build, bundled data lives under `sys._MEIPASS/norefund/<relpath>`.
    """
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "norefund"
    else:
        base = Path(__file__).parent.parent
    return base / relpath


def app_config_dir() -> Path:
    return Path(
        user_config_dir(appname=_APP_NAME, appauthor=_APP_AUTHOR, ensure_exists=True)
    )


def app_log_dir() -> Path:
    return Path(
        user_log_dir(appname=_APP_NAME, appauthor=_APP_AUTHOR, ensure_exists=True)
    )


def app_data_dir() -> Path:
    return Path(
        user_data_dir(appname=_APP_NAME, appauthor=_APP_AUTHOR, ensure_exists=True)
    )


def tiktoken_cache_dir() -> Path:
    """Resolve where tiktoken caches encoding files.

    Respects a user-set TIKTOKEN_CACHE_DIR; otherwise this is the same
    default `main.py` installs at startup (app_data_dir()/tiktoken-cache),
    which survives across runs unlike tiktoken's built-in tempdir default.
    """
    env = os.environ.get("TIKTOKEN_CACHE_DIR")
    if env:
        return Path(env)
    return app_data_dir() / "tiktoken-cache"


def hf_cache_dir() -> Path:
    """Mirror huggingface_hub's own cache resolution logic."""
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE)
