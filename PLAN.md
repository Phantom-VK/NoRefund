# NoRefund — Phase H: Code cleanup

Branch: `ref/code-cleanup` (off `main`). Goal: split the 427-line `core/resources.py` (probe/download/report mixed together) into focused files, and consolidate genuinely duplicated GUI patterns into `gui/widgets.py` — no abstraction beyond what's justified by actual duplication (CLAUDE.md).

## Part 1 — Split `core/resources.py` into a `core/resources/` package
Convert the single 427-line file into a proper submodule package (deliberate deviation from `core/`'s current all-flat-files convention, since a probe/download/report split reads more naturally as a package than as `resources_*.py` siblings). `norefund.core.resources` stays a valid import path throughout — it just now refers to the package, not a module file.
- `core/resources/__init__.py` — re-exports every public **and** underscore-prefixed name from the four submodules below, so `from norefund.core.resources import X` and `norefund.core.resources.X` keep working unchanged everywhere (`tests/test_resources.py` reaches into `resources._capture_tiktoken_blob`, `resources._group_by_resource`, etc. directly, so these must be re-exported too, not just the public surface).
- `core/resources/types.py` — `TokenizerResource`, `ManagedDir`, `ResourceReport`, `ResourceDownloadError`, `DownloadCancelled`, `ProgressFn`.
- `core/resources/probe.py` — `canonical_tiktoken_encoding`, `_capture_tiktoken_blob`, `probe_tiktoken`, `probe_hf`, `_GATED_HF_PREFIXES`. Cache-checking only, deferred `tiktoken`/`huggingface_hub` imports stay local.
- `core/resources/report.py` — `required_tokenizers`, `_group_by_resource`, `dir_stats`, `_managed_dir`, `build_resource_report`.
- `core/resources/download.py` — `_download_tiktoken`, `_download_hf`, `download_tokenizer`. Only submodule that performs network I/O; deferred imports stay local.

**Verified landmine**: `tests/test_resources.py` monkeypatches attributes on the `norefund.core.resources` module object itself (`monkeypatch.setattr(resources, "probe_hf", ...)` at line 144-146; `monkeypatch.setattr("norefund.core.resources._capture_tiktoken_blob", ...)` at lines 224-227/258-261) and then calls `resources.download_tokenizer(...)` expecting the patch to apply inside it. A normal top-level `from norefund.core.resources.probe import ...` in `download.py` would miss these patches (they land on the `norefund.core.resources` package object, i.e. `__init__.py`'s namespace, not on `probe.py`) and silently exercise real tiktoken/huggingface_hub code. Fix: inside `_download_tiktoken`/`_download_hf`, add a deferred `from norefund.core import resources as _resources` (resolves the package, safe — executed at call time, long after `__init__.py` finishes loading, so no circular-import issue despite `download.py` being a submodule of that same package) and call `_resources.probe_tiktoken(...)` / `_resources.probe_hf(...)` / `_resources._capture_tiktoken_blob(...)` as live attribute lookups, same pattern the file already uses for its other deferred imports.

Migration order: `types.py` → `probe.py` → `report.py` → `download.py` (with the fix above) → write `__init__.py` re-exporting everything → delete the old flat `core/resources.py` → run `pytest tests/test_resources.py tests/test_main_view.py tests/test_resources_view.py tests/test_tokenization.py tests/test_compare.py -v`, then full suite + `ruff check src/`.

## Part 2 — GUI widget consolidation
All additions land in the existing `gui/widgets.py`, matching its conventions (type hints, `theme.COLORS`/`theme.font()`, one-line docstrings). Each is independently commit-able/revertable.
- **`ThreadSafeSchedulerMixin`** — wraps the byte-identical `_schedule()` duplicated verbatim in `main_view.py`, `compare_view.py`, `parser_view.py`, `resources_view.py`. Applied via `class X(ThreadSafeSchedulerMixin, ctk.CTkFrame)`; delete each file's local copy and now-dead `TclError` import.
- **`export_via_dialog(*, has_data, extension, filetype_label, content_fn)`** — replaces the structurally-identical `_export_csv`/`_export_md` pairs in `compare_view.py` and `parser_view.py`.
- **`card(parent, **kwargs)`** — factory for the `COLORS["card"]`/`corner_radius=6` frame duplicated in `calculator_view._card()`, `compare_view._card()`, `registry_view._build_card`. (Not applied to `resources_view.py`'s `_TokenizerRow`/`_DirRow` — styling is baked into a subclass `__init__`, different shape, out of scope.)
- **`status_dot(parent, color=..., **kwargs)`** — the 10×10 `corner_radius=5` dot duplicated 3× inside `widgets.py` itself plus `resources_view.py`'s row status dot.
- **`section_label(parent, text, *, size=9, anchor="w", **kwargs)`** — the uppercase/bold/muted header label duplicated in `main_view.py`, `calculator_view.py`, `parser_view.py`, `resources_view.py` (×2). Distinct from `StatPill`'s internal label (non-bold) — not the same thing.
- **`LoadingOverlay`** — controller class wrapping the centered `.place()`/`.place_forget()` label duplicated in `registry_view.py` and `resources_view.py`, both of which reach into `CTkScrollableFrame`'s private `_parent_canvas`; consolidates that reach-in to one place.
- **`EmptyState(ctk.CTkLabel)`** — centered icon+message label duplicated in `compare_view._show_empty_state` and `parser_view._show_empty_results`.

**Explicitly deferred** (judgment calls, not worth the indirection): reusing `ProviderBadge` for `resources_view.py`'s backend pill (different semantics, cosmetic-only match); a shared row/card base class for `_TokenizerRow`/`_DirRow`/compare's result row/registry's model card (data shapes differ enough that a base class likely costs more than it saves).

## Verification
- After Part 1: targeted pytest on the 5 affected test files (especially `test_download_hf_passes_stored_token` and the two `_capture_tiktoken_blob` tests — these silently test nothing if the deferred-lookup fix is missing), then full `pytest` + `ruff check src/`.
- After each Part 2 commit: full `pytest` (existing GUI smoke tests already cover every touched view via `tests/conftest.py`) + `ruff check src/`.
- Manual GUI smoke pass (`python -m norefund.gui.app`): navigate all 5 views, confirm card/section-label/dot rendering unchanged; Resources view scan + successful download + cancelled download + download error (highest-risk path given the Part 1 shim indirection); Registry loading overlay appears/disappears; Compare/Parser empty states, run + CSV/MD export; close app from each view to confirm clean teardown.

## Critical files
- `core/resources.py` (becomes `core/resources/`), `tests/test_resources.py` — split source + the test file with the monkeypatch landmine to respect
- `gui/widgets.py` — target for all new shared components
