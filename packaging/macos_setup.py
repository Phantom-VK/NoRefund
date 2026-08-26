"""py2app setup script for the macOS NoRefund.app bundle.

py2app is the pywebview-recommended packaging path on macOS (pywebview's
macOS backend is a thin PyObjC/WebKit wrapper, not a separate renderer to
choose the way Windows/Linux have one).

Usage (on macOS, inside the project venv with `py2app` installed):
    python packaging/macos_setup.py py2app

Output: dist/NoRefund.app. Not code-signed by this script -- ad-hoc sign
separately (see packaging/README.md) before the first `open`.

Requires the frontend already built at src/norefund/web/ -- packaging/
build.py does this automatically; a direct `py2app` invocation does not.
"""

from __future__ import annotations

from pathlib import Path

from setuptools import setup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src" / "norefund"

APP = [str(SRC / "desktop" / "app.py")]

DATA_FILES = [
    (
        "norefund/config",
        [
            str(SRC / "config" / "default_models.yaml"),
            str(SRC / "config" / "model_architectures.yaml"),
            str(SRC / "config" / "hardware.yaml"),
        ],
    ),
]
# The built frontend, as a directory tree -- without it the app launches to
# a blank window. py2app's data_files wants one (dest_dir, [files]) tuple
# per directory level, not a recursive copy, so walk it ourselves.
_web_dir = SRC / "web"
for _dir in [_web_dir, *(_p for _p in _web_dir.rglob("*") if _p.is_dir())]:
    _files = [str(f) for f in _dir.iterdir() if f.is_file()]
    if _files:
        _dest = "norefund/web" / _dir.relative_to(_web_dir)
        DATA_FILES.append((str(_dest), _files))

OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,  # no .icns yet -- uses the generic app icon
    # reportlab's Type 1 font metrics (AFM data) are package data, not
    # importable modules -- py2app's static analysis can't see them,
    # same reason the PyInstaller spec needs collect_data_files.
    "packages": ["reportlab"],
    # tiktoken discovers its encoding plugins via pkgutil/namespace-package
    # scanning at import time, invisible to static analysis.
    "includes": ["tiktoken_ext", "tiktoken_ext.openai_public"],
    "plist": {
        "CFBundleName": "NoRefund",
        "CFBundleDisplayName": "NoRefund",
        "CFBundleIdentifier": "com.norefund.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        # No entitlements requesting network, camera, microphone or
        # contacts -- the app needs none of them, and requesting them
        # would undermine the "your documents never leave this machine"
        # claim. (No entitlements file at all is not the same as ad-hoc
        # signing with the default entitlements Xcode adds -- see
        # packaging/README.md for the codesign command actually used.)
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
