# PyInstaller spec for NoRefund (Windows/Linux one-dir, windowed build) --
# the React + pywebview desktop app, not the legacy CustomTkinter GUI.
#
# Build (inside the project venv with `pyinstaller` installed):
#   python packaging/build.py
# or directly:
#   pyinstaller packaging/norefund.spec --distpath dist --workpath build
#
# Output lands in dist/NoRefund/ (one-dir build -- an executable plus its
# dependencies, not a single-file bundle). The frontend must already be
# built at src/norefund/web/ (packaging/build.py does this automatically;
# a direct pyinstaller invocation does not). See docs/packaging.md for the
# rationale behind one-dir, the hiddenimports, and why tokenizer caches are
# never bundled.
#
# Linux: WebKitGTK cannot be bundled -- it's a system library with a GObject
# introspection layer, not a Python dependency. Every Linux user needs it
# installed; desktop/app.py's missing_runtime_message() gives them the exact
# install command instead of a traceback.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).parent
SRC = PROJECT_ROOT / "src" / "norefund"

datas = [
    (str(SRC / "config" / "default_models.yaml"), "norefund/config"),
    (str(SRC / "config" / "model_architectures.yaml"), "norefund/config"),
    (str(SRC / "config" / "hardware.yaml"), "norefund/config"),
    # The built frontend -- without this the app launches to a blank window.
    (str(SRC / "web"), "norefund/web"),
]
# reportlab ships its Type 1 font metrics/AFM data as package data, not
# importable modules -- static analysis can't see it, so PDF export would
# fail to find the standard fonts in a frozen build without this.
datas += collect_data_files("reportlab")

hiddenimports = [
    # tiktoken discovers its encoding plugins via pkgutil/namespace-package
    # scanning at import time, which static analysis can't see. Without
    # this, the frozen build fails the first time it loads any encoding.
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
]

# PyGObject looks up gi.overrides.<Module> by name for every gi.repository
# import (the same "discovered at runtime, invisible to static analysis"
# problem as tiktoken_ext above) -- Gtk.py and Gdk.py in there are what
# actually wire up display/window init. Without them, `import gi.repository
# .Gtk` "succeeds" but nothing is initialized, and Gdk.Display.get_default()
# silently returns None instead of a real display -- the frozen build
# looks like it launched fine and then crashes the instant it touches the
# screen list.
hiddenimports += collect_submodules("gi.overrides")

# PyInstaller bundles every pywebview backend it can find on the build
# machine -- an unrelated Qt install would silently double the bundle size
# for a backend the app never uses (desktop/app.py pins gtk on Linux and
# edgechromium on Windows; macOS has no choice of backend).
excludes = [
    "tkinter",
    "customtkinter",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "matplotlib",
    "pytest",
]

a = Analysis(
    [str(SRC / "desktop" / "app.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    cipher=block_cipher,
)

# PyInstaller's binary dependency scan follows PyGObject's compiled _gi
# extension straight to the system's libglib/libgobject/libgio and copies
# them in -- but it does NOT bundle libgtk/libgdk themselves (those are a
# declared system dependency, same as WebKitGTK). The result is a split-
# brain bundle: the system's libgtk-3.so loads, but finds the *bundled*
# glib/gobject copy first via the bundle's library search path instead of
# the system copy it was actually built against, and silently fails to get
# a display (Gdk.Display.get_default() returns None) instead of erroring.
# Excluding them here makes the whole glib/gtk stack come from the system,
# consistently, on every Linux install that already satisfies the
# WebKitGTK dependency in missing_runtime_message().
_glib_stack_prefixes = (
    "libglib-2.0",
    "libgobject-2.0",
    "libgio-2.0",
    "libgmodule-2.0",
    "libgirepository",
)
a.binaries = [b for b in a.binaries if not b[0].startswith(_glib_stack_prefixes)]

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
