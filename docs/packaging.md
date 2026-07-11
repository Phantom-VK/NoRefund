# Packaging readiness (design)

This documents the plan for building installers on each OS. No installer is
built yet — this phase only audits the codebase for packaging-safety and
records the approach so it can be executed without further design work.

## Audit results

- All read-only bundled resources (currently: `config/default_models.yaml`)
  are resolved through `core/paths.bundled_resource()`, which checks
  `sys._MEIPASS` first and falls back to the source-tree path — safe for a
  frozen PyInstaller build.
- All writable state (settings, logs, tiktoken cache, HF cache) goes through
  `core/paths.py`, backed by `platformdirs` — no writes under the install
  directory, no admin rights required for normal use.
- No code depends on `__file__`, `os.getcwd()`, or `sys.argv[0]` outside of
  `core/paths.py` itself.
- `main.py` sets `TIKTOKEN_CACHE_DIR` (via `paths.tiktoken_cache_dir()`)
  before any tiktoken import, so tokenizer downloads persist across runs
  instead of landing in a tempdir that gets wiped.

## PyInstaller spec outline (to become `packaging/norefund.spec`)

- One-dir, windowed build (`console=False`) — the app is GUI-only.
- `datas`: bundle `src/norefund/config/default_models.yaml`, plus
  `collect_data_files("customtkinter")` for its theme JSON assets. Add
  `collect_data_files("tkinterdnd2")` if the `dnd` optional dependency is
  bundled.
- `hiddenimports`: **`tiktoken_ext`** and **`tiktoken_ext.openai_public`**.
  tiktoken discovers its encoding plugins via `pkgutil`/namespace-package
  scanning at runtime, which static analysis can't see — PyInstaller will
  silently omit them without this hint, and the app will fail the first
  time it tries to load any tiktoken encoding.
- Do not bundle tokenizer caches (tiktoken vocab files, HF `tokenizer.json`)
  in the installer — see "Do not bundle" below.

## Per-OS targets (record now, build later)

- **Windows**: Inno Setup `.iss` script; per-user install (no admin
  elevation required); Start Menu shortcut; uninstaller entry.
- **macOS**: `.app` bundle via PyInstaller, packaged with `create-dmg`;
  notarization required for Gatekeeper — deferred until there's an Apple
  Developer account to sign with.
- **Linux**: AppImage as the primary target (works across distros without
  install); fallback is a plain tarball + a `.desktop` file for users who
  prefer to unpack manually.

## Do not bundle tokenizer caches

Tokenizer vocab files are not shipped in any installer:

- **Size** — bundling all backends would multiply installer size for
  something most users only need for 1–2 models.
- **Licensing** — HF tokenizer files carry their own model licenses,
  separate from NoRefund's.
- **Staleness** — bundled copies would go stale; the Resources view's
  one-click download always fetches current files.

The Resources view (with the first-run banner pointing to it) is the
intended post-install acquisition path for every user, packaged or not.
