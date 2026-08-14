# PyInstaller spec for NoRefund (Windows one-dir, windowed build).
#
# Build (on Windows, inside the project venv with `pyinstaller` installed):
#   pyinstaller packaging/norefund.spec --distpath dist --workpath build
#
# Output lands in dist/NoRefund/ (one-dir build — an .exe plus its
# dependencies, not a single-file bundle). See docs/packaging.md for the
# rationale behind one-dir, the hiddenimports, and why tokenizer caches
# are never bundled.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).parent
SRC = PROJECT_ROOT / "src" / "norefund"

datas = [
    (str(SRC / "config" / "default_models.yaml"), "norefund/config"),
    (str(SRC / "config" / "model_architectures.yaml"), "norefund/config"),
    (str(SRC / "config" / "hardware.yaml"), "norefund/config"),
]
datas += [
    (str(icon_path), "norefund/assets/icons")
    for icon_path in (SRC / "assets" / "icons").iterdir()
    if icon_path.is_file()
]
datas += [
    (str(icon_path), "norefund/assets/icons/providers")
    for icon_path in (SRC / "assets" / "icons" / "providers").iterdir()
]
datas += collect_data_files("customtkinter")

hiddenimports = [
    # PIL.ImageTk resolves this at runtime via a try/except import to find
    # the right _tkinter shared library; PyInstaller's static analysis can't
    # see that either, so every CTkImage-bearing widget (i.e. every icon)
    # fails with "No module named 'PIL._tkinter_finder'" without this.
    "PIL._tkinter_finder",
    # tiktoken discovers its encoding plugins via pkgutil/namespace-package
    # scanning at import time, which static analysis can't see. Without
    # this, the frozen build fails the first time it loads any encoding.
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
]

# Drag-and-drop is an optional extra ([project.optional-dependencies] dnd);
# bundle it only if it's actually installed in the build environment.
try:
    import tkinterdnd2  # noqa: F401

    datas += collect_data_files("tkinterdnd2")
    hiddenimports.append("tkinterdnd2")
except ImportError:
    pass

a = Analysis(
    [str(PROJECT_ROOT / "src" / "norefund" / "main.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NoRefund",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="NoRefund",
)
