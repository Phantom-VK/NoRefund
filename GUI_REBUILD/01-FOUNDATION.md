# Phase 01 — Foundation: Vite scaffold + pywebview shell

**Branch:** `feat/rebuild-01-foundation`
**Depends on:** nothing
**Prerequisite reading:** `GUI_REBUILD/00-OVERVIEW.md` (all of it)

**Goal:** A window opens on all three OSes, rendering a React app, with a
working dev loop (hot reload) and a working production loop (built assets).

**Out of scope for this phase:** any NoRefund UI, any `core/` call, any styling
beyond proving Tailwind compiles. No sidebar, no views, no bridge methods.

---

## Files

- Create: `frontend/package.json`, `frontend/vite.config.ts`,
  `frontend/tsconfig.json`, `frontend/index.html`,
  `frontend/src/main.tsx`, `frontend/src/App.tsx`,
  `frontend/src/styles/index.css`
- Create: `src/norefund/desktop/__init__.py`, `src/norefund/desktop/app.py`
- Create: `tests/test_desktop_app.py`
- Modify: `pyproject.toml` (add `pywebview`), `.gitignore`

## Interfaces produced

Later phases rely on exactly these names:

```python
# src/norefund/desktop/app.py
WEB_DIR: Path                     # built frontend assets, packaging-safe
DEV_SERVER_URL: str               # "http://localhost:5173"

def resolve_entrypoint() -> str | Path
def preferred_gui() -> str | None
def missing_runtime_message() -> str | None
def create_app_window(js_api: object | None = None) -> "webview.Window"
def main() -> None
```

---

## Task 1: Vite + React + TypeScript + Tailwind scaffold

**Why these versions:** they match the Figma Make export exactly, so its 48 UI
primitives copy in without a migration (`00-OVERVIEW.md` §3).

- [x] **Step 1.1: Create `frontend/package.json`**

```json
{
  "name": "norefund-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "lucide-react": "0.487.0",
    "class-variance-authority": "0.7.1",
    "clsx": "2.1.1",
    "tailwind-merge": "3.2.0"
  },
  "devDependencies": {
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "@vitejs/plugin-react": "4.7.0",
    "@tailwindcss/vite": "4.1.12",
    "tailwindcss": "4.1.12",
    "typescript": "5.6.3",
    "vite": "6.3.5"
  }
}
```

Radix packages are **not** added here. Phase 02 adds only the ones actually
used, copied from the Figma design's `package.json`.

- [x] **Step 1.2: Create `frontend/vite.config.ts`**

The `outDir` is the critical line — Vite's default `dist/` collides with
PyInstaller's `dist/` (documented pywebview pitfall, `00-OVERVIEW.md` §10).

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Assets are loaded from file:// or the bundled http server, never a
  // domain root — relative base is required or every asset 404s.
  base: "./",
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  build: {
    outDir: resolve(__dirname, "../src/norefund/web"),
    emptyOutDir: true,
    target: "es2022",
    sourcemap: false,
  },
  server: { port: 5173, strictPort: true },
});
```

- [x] **Step 1.3: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src"]
}
```

- [x] **Step 1.4: Create `frontend/index.html`**

The CSP meta tag enforces the "no remote assets" constraint at runtime, so a
stray CDN import fails loudly in development instead of silently in production.

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta
      http-equiv="Content-Security-Policy"
      content="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'"
    />
    <title>NoRefund</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [x] **Step 1.5: Create `frontend/src/styles/index.css`**

```css
@import "tailwindcss";

html,
body,
#root {
  height: 100%;
  margin: 0;
}

body {
  font-family:
    Inter, "Segoe UI", -apple-system, BlinkMacSystemFont, Helvetica, Arial,
    sans-serif;
  /* The window chrome is native; the page must never scroll as a whole.
     Individual panes own their own overflow. */
  overflow: hidden;
}
```

- [x] **Step 1.6: Create `frontend/src/main.tsx` and `frontend/src/App.tsx`**

```tsx
// main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles/index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

```tsx
// App.tsx
export default function App() {
  const bridged =
    typeof window !== "undefined" && "pywebview" in window ? "yes" : "no";
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2">
      <h1 className="text-2xl font-bold">NoRefund</h1>
      <p className="text-sm opacity-60">Phase 01 — foundation</p>
      <p className="text-xs opacity-40">bridge present: {bridged}</p>
    </div>
  );
}
```

- [x] **Step 1.7: Verify the frontend builds**

```bash
cd frontend && npm install && npm run typecheck && npm run build
```
Expected: typecheck prints nothing and exits 0; build writes
`src/norefund/web/index.html` plus an `assets/` directory.

- [x] **Step 1.8: Commit**

```bash
git add frontend/ .gitignore
git commit -m "feat(frontend): scaffold Vite + React + TypeScript + Tailwind"
```

---

## Task 2: Python dependency and ignore rules

- [x] **Step 2.1: Add pywebview to `pyproject.toml`**

Add to `[project].dependencies`:

```toml
    "pywebview>=6.2.1",
```

Add a new optional group (the Linux GTK bindings cannot be pulled in
unconditionally — they fail to build on Windows and macOS):

```toml
[project.optional-dependencies]
linux = [
    "pygobject>=3.50",
]
```

Do **not** remove `customtkinter` yet. Phase 13 does that, after `gui/` is gone.

- [x] **Step 2.2: Add build output to `.gitignore`**

```gitignore
# Built frontend assets — produced by `cd frontend && npm run build`
/src/norefund/web/
/frontend/node_modules/
```

- [x] **Step 2.3: Install and verify**

```bash
pip install -e . && python -c "import webview; print(webview.__version__)"
```
Expected: `6.2.1` or higher.

On Linux, PyGObject is also required for the WebKitGTK backend:
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
python -c "import gi; gi.require_version('WebKit2','4.1'); print('webkit ok')"
```
Expected: `webkit ok`. **If this fails, fix it before Step 3** — every later
phase needs a window to open.

- [x] **Step 2.4: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "build: add pywebview dependency and frontend build ignores"
```

---

## Task 3: The pywebview shell

This is the only Python file in the phase. It must handle three things the Tk
app got wrong (`GUI_REVIEW.md` §3.2): window sizing against the real screen,
graceful failure when a runtime is missing, and dev-vs-frozen asset resolution.

- [x] **Step 3.1: Write the failing test — `tests/test_desktop_app.py`**

```python
"""Entrypoint resolution and runtime checks for the desktop shell.

No window is created here — pywebview needs a real display. These cover the
pure decision logic that would otherwise only fail at launch time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from norefund.desktop import app as desktop_app


def test_dev_entrypoint_used_when_env_var_set(monkeypatch):
    monkeypatch.setenv("NOREFUND_DEV", "1")
    assert desktop_app.resolve_entrypoint() == desktop_app.DEV_SERVER_URL


def test_built_entrypoint_used_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("NOREFUND_DEV", raising=False)
    index = tmp_path / "index.html"
    index.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(desktop_app, "WEB_DIR", tmp_path)
    assert desktop_app.resolve_entrypoint() == index


def test_missing_build_raises_actionable_error(monkeypatch, tmp_path):
    monkeypatch.delenv("NOREFUND_DEV", raising=False)
    monkeypatch.setattr(desktop_app, "WEB_DIR", tmp_path / "nope")
    with pytest.raises(RuntimeError, match="npm run build"):
        desktop_app.resolve_entrypoint()


def test_preferred_gui_is_platform_appropriate(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert desktop_app.preferred_gui() == "gtk"
    monkeypatch.setattr(sys, "platform", "win32")
    assert desktop_app.preferred_gui() == "edgechromium"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert desktop_app.preferred_gui() is None


def test_window_size_is_clamped_to_small_screens():
    # 1366x768 is still a very common Windows laptop panel; the Tk build's
    # minsize(1180, 760) made the app impossible to fit on one.
    w, h = desktop_app.initial_window_size(1366, 768)
    assert w <= 1366 and h <= 768 - 40


def test_window_size_uses_preferred_on_large_screens():
    w, h = desktop_app.initial_window_size(2560, 1440)
    assert (w, h) == (1440, 900)


def test_missing_runtime_message_is_none_when_backend_importable(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert desktop_app.missing_runtime_message() is None
```

- [x] **Step 3.2: Run it and watch it fail**

```bash
pytest tests/test_desktop_app.py -v
```
Expected: collection error — `ModuleNotFoundError: No module named 'norefund.desktop'`.

- [x] **Step 3.3: Create `src/norefund/desktop/__init__.py`**

```python
"""Desktop shell: pywebview window, JS bridge, and DTO marshalling.

Holds no business logic — every computation lives in `norefund.core`. This
package only creates the window, exposes `core` to JavaScript, and converts
dataclasses to JSON-safe dicts.
"""

from __future__ import annotations
```

- [x] **Step 3.4: Create `src/norefund/desktop/app.py`**

```python
"""Window creation and lifecycle for the NoRefund desktop app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import webview

from norefund.core.paths import bundled_resource

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
        resolve_entrypoint(),
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
    create_app_window()
    webview.start(
        gui=preferred_gui(),
        debug=os.environ.get("NOREFUND_DEV") == "1",
        private_mode=True,
    )


if __name__ == "__main__":
    main()
```

- [x] **Step 3.5: Make `bundled_resource("web")` resolvable**

`core/paths.bundled_resource` resolves against the installed package root, so
`src/norefund/web/` works in a source checkout and in a frozen build with no
change. Confirm:

```bash
python -c "from norefund.core.paths import bundled_resource; print(bundled_resource('web'))"
```
Expected: a path ending in `src/norefund/web`. **If it raises or points
elsewhere, stop and report** — do not patch `core/paths.py`.

- [x] **Step 3.6: Run the tests**

```bash
pytest tests/test_desktop_app.py -v
```
Expected: 7 passed.

- [ ] **Step 3.7: Launch the real window**

```bash
cd frontend && npm run build && cd ..
python -m norefund.desktop.app
```
Expected: a window titled "NoRefund — Token & Cost Analyzer" showing the
heading and `bridge present: yes`.

- [x] **Step 3.8: Commit**

```bash
git add src/norefund/desktop/ tests/test_desktop_app.py
git commit -m "feat(desktop): add pywebview shell with cross-OS runtime checks"
```

---

## Task 4: Developer loop

- [x] **Step 4.1: Create `frontend/README.md`**

```markdown
# NoRefund frontend

## Develop (hot reload)

Two terminals:

    cd frontend && npm run dev          # Vite on :5173
    NOREFUND_DEV=1 python -m norefund.desktop.app

The window loads from the dev server, so React edits hot-reload in place.
`NOREFUND_DEV=1` also enables the webview devtools (right-click → Inspect).

## Build (what ships)

    cd frontend && npm run build        # emits ../src/norefund/web/
    python -m norefund.desktop.app

## Rules

- No remote assets. The CSP in `index.html` blocks them.
- No new dependency without a line in the relevant `GUI_REBUILD/` phase file.
```

- [ ] **Step 4.2: Verify hot reload**

Start both processes. Edit the `<p>` text in `App.tsx`. Expected: the window
updates without a restart.

- [x] **Step 4.3: Commit**

```bash
git add frontend/README.md
git commit -m "docs(frontend): document the dev and build loops"
```

---

## Definition of Done

- [x] `cd frontend && npm run typecheck` → 0 errors
- [x] `cd frontend && npm run build` → writes `src/norefund/web/index.html`
- [x] `pytest` → all green (7 new tests, existing suite unaffected — 267 passed)
- [x] `ruff check src/` → clean
- [ ] `python -m norefund.desktop.app` opens a window showing `bridge present: yes`
      — **blocked on this dev machine**: `libgirepository-2.0-dev` is not
      installed and sudo is unavailable non-interactively. Running it instead
      correctly triggers `missing_runtime_message()` and exits 2 (see next
      item — this doubles as a real, non-monkeypatched confirmation of that
      path). Needs manual verification once the system package is installed.
- [ ] `NOREFUND_DEV=1` + `npm run dev` gives working hot reload
      — Vite dev server confirmed serving `main.tsx` with React Fast Refresh
      injected (`curl localhost:5173`). The pywebview-side half is blocked by
      the same missing runtime as above; needs manual verification once
      resolved.
- [x] Uninstalling the GTK bindings on Linux produces the actionable install
      message and exit code 2, not a traceback — verified for real (not
      simulated): `gi` is genuinely absent on this machine, so
      `python -m norefund.desktop.app` printed the actionable message and
      exited 2.

## PR description

```markdown
Phase 01 of the GUI rebuild (see GUI_REBUILD/01-FOUNDATION.md).

Scaffolds the React frontend and the pywebview shell. No NoRefund UI yet —
the window renders a placeholder and reports whether the JS bridge is present.

- frontend/: Vite 6 + React 18.3.1 + TS strict + Tailwind 4, versions pinned to
  match the Figma Make export so its UI primitives copy in unmodified
- Vite emits to src/norefund/web/ rather than dist/, which would collide with
  PyInstaller's dist/
- src/norefund/desktop/app.py: window creation, per-platform renderer pinning,
  screen-size clamping (fixes GUI_REVIEW.md §3.2 — the old minsize did not fit
  a 1366x768 panel), and an actionable message when the system webview runtime
  is missing instead of a traceback
- CSP in index.html enforces the no-remote-assets rule at runtime

core/ is untouched. gui/ is untouched and still runnable.
```
