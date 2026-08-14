# Registry Skeleton Atomic Reveal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Model Registry's per-card skeleton→real-card swap (which pops cards in one-by-one and looks janky) with a single atomic reveal: skeleton grid shows immediately, real cards build off-screen in the background, and the whole grid swaps from skeleton to real in one layout pass once building finishes and a minimum dwell time has elapsed.

**Architecture:** `RegistryView._start_loading()` still builds and grids the skeleton cards instantly and starts the glow animation (unchanged). Real cards are now constructed off-screen (built but never gridded) via chunked `after(1, ...)` calls so the event loop stays free. A parallel `after(_MIN_SKELETON_MS, ...)` timer enforces a minimum skeleton dwell. When both "all real cards built" and "dwell elapsed" are true, `_maybe_reveal()` destroys all skeletons, swaps `self._cards` to the real cards, and calls the existing `_relayout(force=True)` once — a single grid pass instead of N.

**Tech Stack:** Python 3.12, CustomTkinter, pytest (GUI smoke test runs against a real/virtual X11 display via Tk's `after`/`update` event loop).

## Global Constraints

- `from __future__ import annotations` at the top of any new file (CLAUDE.md convention).
- GUI issues definition of done (CLAUDE.md): (1) no crash, (2) app closes cleanly, (3) edge cases (zero models, one model, mid-load navigation) don't raise.
- Keep the working mouse-wheel scrolling (`bind_mousewheel`) and bounded-scroll (`_refresh_scrollregion`) fixes untouched — out of scope for this change.
- `ruff check src/` must stay clean; `pytest` must stay green (excluding the pre-existing environment-only tokenizer-cache failures noted in HANDOFF.md).
- Minimum skeleton dwell time: 500ms (within the 400–600ms range agreed with the user).

---

### Task 1: Atomic reveal for Registry skeleton loading

**Files:**
- Modify: `src/norefund/gui/registry_view.py:1-154` (imports/constants block, `__init__`, and the skeleton-loading section)
- Create: `tests/test_registry_view_loading.py`

**Interfaces:**
- Consumes: `RegistryView(parent, shell)` where `shell.models: list[ModelInfo]` (existing constructor signature, unchanged). `norefund.core.models_registry.list_models()` for real test data.
- Produces (new symbols other code/tests may rely on):
  - Module-level constant `_MIN_SKELETON_MS: int` in `registry_view.py`.
  - Instance attrs on `RegistryView`: `self._skeletons: list[ctk.CTkFrame]`, `self._real_cards: list[ctk.CTkFrame | None]`, `self._dwell_done: bool`, `self._build_done: bool`.
  - Methods: `_mark_dwell_done(self) -> None`, `_build_next_real_card(self, index: int) -> None` (replaces `_build_next_card`), `_maybe_reveal(self) -> None`.
  - `self._cards: list[tuple[ModelInfo, ctk.CTkFrame]]` keeps its existing shape/meaning (consumed by `_visible_cards`, `_relayout`) — during the skeleton phase it holds `(model, skeleton_frame)` pairs, and after reveal it holds `(model, real_card_frame)` pairs, exactly as before the change.

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_registry_view_loading.py`:

```python
"""Smoke tests for RegistryView's skeleton-loading / atomic-reveal flow.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import pytest

ctk = pytest.importorskip("customtkinter")

from norefund.core.models_registry import list_models  # noqa: E402
from norefund.gui.registry_view import _MIN_SKELETON_MS, RegistryView  # noqa: E402


@dataclass
class _FakeShell:
    models: list


@pytest.fixture
def root():
    try:
        r = ctk.CTk()
        r.withdraw()
    except Exception as exc:  # no display available
        pytest.skip(f"no Tk display available: {exc}")
    yield r
    r.destroy()


def _pump(root, ms: int) -> None:
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        root.update()


def _pump_until(root, predicate, timeout_ms: int = 3000) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        root.update()
        if predicate():
            return
    pytest.fail("condition not met within timeout")


def test_skeleton_shows_first_then_atomic_reveal(root):
    shell = _FakeShell(models=list_models())
    start = time.monotonic()
    view = RegistryView(root, shell)
    original_skeletons = list(view._skeletons)
    assert original_skeletons, "expected at least one skeleton card"

    relayout_calls: list[list] = []
    original_relayout = view._relayout

    def spy_relayout(force=False):
        relayout_calls.append(list(view._cards))
        return original_relayout(force)

    view._relayout = spy_relayout

    # Shortly after construction we should still be mid-skeleton-phase.
    _pump(root, 30)
    assert view._loading is True
    assert all(card in original_skeletons for _model, card in view._cards)

    _pump_until(root, lambda: not view._loading)
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms >= _MIN_SKELETON_MS - 20  # scheduler slack

    assert view._skeletons == []
    for skeleton in original_skeletons:
        assert skeleton.winfo_exists() == 0

    assert len(view._cards) == len(shell.models)
    for _model, card in view._cards:
        assert card not in original_skeletons
        assert card.grid_info() != {}

    # Every recorded _relayout call graded either all-skeleton or all-real
    # cards -- never a mix. That's what "atomic reveal" means here.
    assert relayout_calls, "expected at least one _relayout call"
    for snapshot in relayout_calls:
        cards_only = [card for _model, card in snapshot]
        is_all_skeleton = all(c in original_skeletons for c in cards_only)
        is_all_real = all(c not in original_skeletons for c in cards_only)
        assert is_all_skeleton or is_all_real

    final_cards = [card for _model, card in relayout_calls[-1]]
    assert final_cards and all(c not in original_skeletons for c in final_cards)


def test_navigating_away_mid_load_does_not_crash(root):
    shell = _FakeShell(models=list_models())
    view = RegistryView(root, shell)
    _pump(root, 20)
    assert view._loading is True
    view.destroy()
    # Pending after() callbacks (dwell timer, next-card builder) must not
    # raise once the widget they target is gone.
    _pump(root, 700)


def test_zero_models_does_not_crash(root):
    shell = _FakeShell(models=[])
    view = RegistryView(root, shell)
    _pump_until(root, lambda: not view._loading)
    assert view._cards == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `DISPLAY=:1 pytest tests/test_registry_view_loading.py -v` (adjust `DISPLAY` to match the available X server; use `xvfb-run -a pytest tests/test_registry_view_loading.py -v` if no display is otherwise available)

Expected: FAIL/ERROR — `ImportError: cannot import name '_MIN_SKELETON_MS'` (constant doesn't exist yet), since the current implementation grids real cards one at a time instead of building them off-screen.

- [ ] **Step 3: Implement the atomic-reveal loading flow**

In `src/norefund/gui/registry_view.py`, add the new constant next to the existing glow constants (around line 16-18):

```python
_MIN_CARD_WIDTH = 300
_GLOW_INTERVAL_MS = 60
_GLOW_STEP = 0.18
_GLOW_MAX_ALPHA = 0.4
_MIN_SKELETON_MS = 500
```

In `__init__` (currently lines 22-36), add the new tracking attributes alongside the existing ones:

```python
    def __init__(self, parent, shell) -> None:
        super().__init__(parent, fg_color=COLORS["bg"])
        self.shell = shell
        self._active_provider = "All"
        self._pills: dict[str, ctk.CTkButton] = {}
        self._cards: list[tuple[ModelInfo, ctk.CTkFrame]] = []
        self._skeletons: list[ctk.CTkFrame] = []
        self._real_cards: list[ctk.CTkFrame | None] = []
        self._dwell_done = False
        self._build_done = False
        self._glow_widgets: list[ctk.CTkFrame] = []
        self._glow_phase = 0.0
        self._loading = False
        self._last_col_count = -1

        self._build_header()
        self._build_grid()
        bind_mousewheel(self._scroll)
        self._start_loading()
```

Replace the whole skeleton-loading section (currently `_start_loading` through the end of `_build_next_card`, lines 109-141) with:

```python
    def _start_loading(self) -> None:
        self._loading = True
        self._dwell_done = False
        self._build_done = False
        self._skeletons = [self._build_skeleton_card() for _ in self.shell.models]
        self._real_cards = [None] * len(self.shell.models)
        self._cards = list(zip(self.shell.models, self._skeletons))
        self._sync_pill_enabled()
        self.after(50, self._relayout, True)
        self._animate_glow()
        self.after(_MIN_SKELETON_MS, self._mark_dwell_done)
        self.after(1, self._build_next_real_card, 0)

    def _mark_dwell_done(self) -> None:
        if not self.winfo_exists():
            return
        self._dwell_done = True
        self._maybe_reveal()

    def _build_next_real_card(self, index: int) -> None:
        if not self.winfo_exists():
            return
        if index >= len(self.shell.models):
            self._build_done = True
            self._maybe_reveal()
            return
        # Built off-screen (never gridded here) so the skeleton->real swap
        # happens as a single reveal in _maybe_reveal, not as len(models)
        # separate visible layout passes.
        self._real_cards[index] = self._build_card(self.shell.models[index])
        self.after(1, self._build_next_real_card, index + 1)

    def _maybe_reveal(self) -> None:
        if not (self._dwell_done and self._build_done):
            return
        if not self.winfo_exists():
            return
        self._loading = False
        self._glow_widgets = []
        for skeleton in self._skeletons:
            skeleton.destroy()
        self._skeletons = []
        self._cards = list(zip(self.shell.models, self._real_cards))
        self._real_cards = []
        self._sync_pill_enabled()
        self._relayout(force=True)
```

Note: `_refresh_scrollregion()` no longer needs an explicit standalone call at the end of loading — `_relayout(force=True)` already calls it (see existing line 362), so the reveal gets a correctly bounded scrollregion for free.

- [ ] **Step 4: Run the test to verify it passes**

Run: `DISPLAY=:1 pytest tests/test_registry_view_loading.py -v` (or `xvfb-run -a pytest tests/test_registry_view_loading.py -v`)

Expected: PASS (3 passed)

- [ ] **Step 5: Lint**

Run: `ruff check src/norefund/gui/registry_view.py tests/test_registry_view_loading.py`

Expected: no errors

- [ ] **Step 6: Commit**

```bash
git add src/norefund/gui/registry_view.py tests/test_registry_view_loading.py
git commit -m "fix(gui): atomic skeleton-to-real-card reveal in Model Registry"
```

---

### Task 2: Full-suite verification and manual check

**Files:**
- None modified — verification only.

**Interfaces:**
- Consumes: Task 1's finished `RegistryView`.
- Produces: nothing new; this task is a gate, not a deliverable.

- [ ] **Step 1: Run the full test suite**

Run: `xvfb-run -a pytest` (or plain `pytest` if `DISPLAY` is already set)

Expected: all tests pass except the pre-existing environment-only tokenizer-cache failures already noted in HANDOFF.md (unrelated to this change).

- [ ] **Step 2: Run the full lint pass**

Run: `ruff check src/`

Expected: no errors

- [ ] **Step 3: Automated crash/close-clean check**

Run this inline smoke script to confirm the full app (not just the isolated view) survives constructing and tearing down the Registry mid-load:

```bash
DISPLAY=:1 python3 -c "
import customtkinter as ctk
from norefund.gui.main_view import MainView

root = ctk.CTk()
root.withdraw()
mv = MainView(root)
mv.show_view(MainView.VIEW_REGISTRY)
for _ in range(10):
    root.update()
root.destroy()
print('closed cleanly')
"
```

Expected: prints `closed cleanly`, no traceback.

- [ ] **Step 4: Manual verification on real desktop (not the sandbox)**

This is the step that actually answers the open question from PLAN.md: does the atomic reveal look and feel right? Launch the real app (`python -m norefund.gui.app`), open the Model Registry a few times, and confirm:
- The skeleton grid appears immediately (no blank flash).
- It stays visible for a beat (not a sub-100ms flicker).
- All real cards appear together in one swap — no one-by-one pop-in.
- Filtering by provider and resizing the window still work during and after load.
- Mouse-wheel scrolling and scroll bounds (the two things HANDOFF.md already marked working) are still fine.

If this still looks/feels janky, that's the signal to fall back to PLAN.md's Phase 2 (ditch skeleton/glow, use a dimmed-scrim + spinner overlay instead) — report back rather than silently reworking it further.

- [ ] **Step 5: Commit (only if Step 3's script or any fixups changed files)**

Skip if Task 1's commit already covers everything and no fixes were needed here.

---

## Self-Review Notes

- **Spec coverage:** PLAN.md Phase 1's four points (instant skeleton grid + glow, off-screen build, minimum dwell, atomic reveal) are all implemented in Task 1, Step 3. Phase 2 is explicitly deferred to a manual decision gate in Task 2 Step 4, matching the user's "try to fix it first" instruction.
- **Placeholder scan:** none found — all steps have concrete code/commands.
- **Type consistency:** `self._cards` keeps its pre-existing `list[tuple[ModelInfo, ctk.CTkFrame]]` shape throughout, so `_visible_cards()` and `_relayout()` (unmodified) keep working without changes. `_real_cards` is typed `list[ctk.CTkFrame | None]` while being built, then zipped into `_cards` (never `None` at that point since it's only read after `_build_done`).
