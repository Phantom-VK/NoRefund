# Packaging NoRefund

One command builds a distributable on any platform:

```bash
python packaging/build.py
```

This always rebuilds the frontend first (`npm ci && npm run build` in
`frontend/`) unless you pass `--skip-frontend`, and refuses to proceed if
`src/norefund/web/index.html` is missing or older than the newest file in
`frontend/src/` -- a stale bundled UI is a silent, hard-to-notice bug, not
a convenience worth risking.

It dispatches to PyInstaller on Windows/Linux and py2app on macOS.

## Linux

**Build prerequisites:**

```bash
pip install -e ".[dev,linux]"
```

`pyinstaller` comes from the `dev` extra; `pygobject` (the Python GTK
bindings) from `linux`. You also need the system GTK/WebKitGTK packages
themselves -- see "End-user requirements" below, since the build machine
needs the same runtime the app does to even launch for testing.

**Build:**

```bash
python packaging/build.py
```

**Output:** `dist/NoRefund/` (a one-dir build -- an executable plus its
dependencies, not a single-file bundle). Launch with
`./dist/NoRefund/NoRefund`.

**End-user requirements:** WebKitGTK is a system library with a GObject
introspection layer, not something any Python packager can bundle -- every
Linux user needs it installed already. This is not a workaround; it's how
every webview-based desktop app behaves on Linux, PyInstaller or not.

```bash
# Debian/Ubuntu
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1

# Fedora
sudo dnf install python3-gobject webkit2gtk4.1

# Arch
sudo pacman -S python-gobject webkit2gtk-4.1
```

These are the exact strings `missing_runtime_message()` in
`src/norefund/desktop/app.py` prints when the runtime is missing --
**keep the two in sync**. If the app is launched without WebKitGTK
installed, it prints this message to stderr and exits with code 2,
rather than an unhandled traceback.

**Known limitation:** the frozen build was made to work by excluding
PyInstaller's bundled copies of libglib/libgobject/libgio (see the
comment in `packaging/norefund.spec`) so the whole GTK stack resolves
from the system consistently. If a future PyInstaller/PyGObject upgrade
changes what gets auto-bundled, re-verify by actually launching
`dist/NoRefund/NoRefund` -- a build that compiles is not a build that
works, and this exact class of bug (a silent `Gdk.Display.get_default()
== None` instead of an import error) does not show up any other way.

## Windows

**Build prerequisites:**

```powershell
pip install -e ".[dev]"
```

**Build:**

```powershell
python packaging\build.py
```

**Output:** `dist\NoRefund\NoRefund.exe`. `packaging\windows\build.ps1`
wraps the same PyInstaller spec and additionally produces a signed-free
Inno Setup installer (`packaging\windows\installer.iss`) if `iscc` is on
`PATH` -- see that script's own header comment.

**End-user requirements:** Microsoft Edge WebView2 runtime. Present on
Windows 11 and most Windows 10 installs already, but not guaranteed. If
missing, the app prints an actionable message with the download link
(`https://developer.microsoft.com/microsoft-edge/webview2/`) and exits
with code 2, rather than a traceback.

**Known limitation:** no code-signing certificate. Windows SmartScreen
will warn on first run of an unsigned installer/exe.

## macOS

**Build prerequisites:**

```bash
pip install -e ".[dev,macos]"
```

**Build:**

```bash
python packaging/build.py
```

**Output:** `dist/NoRefund.app`. Not code-signed by `build.py` -- ad-hoc
sign it yourself before the first launch:

```bash
codesign --force --deep --sign - dist/NoRefund.app
open dist/NoRefund.app
```

**End-user requirements:** none beyond macOS 12+ -- WebKit is part of the
OS, unlike Linux's WebKitGTK.

**Known limitation:** notarisation is out of scope (it needs a paid Apple
Developer account). The app is only ad-hoc signed, so Gatekeeper will
block a plain double-click on first launch. End users need to
**right-click the app -> Open**, confirm once in the dialog that appears,
and it launches normally on every run after that.

## What is never bundled, on any platform

Tokenizer caches (tiktoken vocab files, HuggingFace `tokenizer.json`
files) are never shipped in any build. They're large, backend-specific,
and the whole point of the Resources view is that a user downloads only
the tokenizers they actually need, on their own machine, on their own
network connection -- bundling any of them would both bloat every install
and quietly contradict "your documents never leave this machine" by
shipping a pre-populated cache nobody asked for.
