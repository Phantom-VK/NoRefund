# NoRefund Evolution Plan — Desktop-first, Resources Manager, Compare, Packaging Readiness

> **Deliverable of this task**: write this plan (adapted) into the repo's `PLAN.md` for later execution. No code changes yet — the user asked for the plan document only.

## Context

NoRefund currently brands itself "offline-first" and refuses all network access — missing tokenizer caches raise errors telling the user to run a `python -c ...` command manually. The user wants to reposition as **desktop-first, privacy-respecting**: analysis stays 100% local, but the app may download tokenizers on explicit user action. A new **Resources** GUI section will show which tokenizers are cached, where they live on disk, their sizes, and offer one-click downloads. Future distribution targets Windows (PyInstaller + Inno Setup), macOS, and Linux — architecture must become frozen-app-safe now, installers built later. Differentiators chosen by user: **cost/compare workflows** and **polish & distribution**.

Confirmed decisions:
- In-app download button per missing tokenizer (network only on explicit click).
- Packaging: design-for-it-now, build installers in a later phase.
- Differentiators: multi-model compare/export + first-run/DnD/UX polish. (Live registry updates and per-page insight explicitly deferred.)

## Key codebase facts

- `core/tokenization.py`: `TikTokenBackend` blocks network by monkey-patching `tiktoken.load.read_file`; `HFTokenizerBackend` uses `hf_hub_download(..., local_files_only=True)`. Module-level `_tokenizer_cache` memoizes backends.
- `core/models_registry.py`: `ModelInfo` dataclass, loads `config/default_models.yaml` (11 models) via `__file__`-relative `_DEFAULT_REGISTRY_PATH`.
- `core/settings.py`: `Settings` + `SettingsStore` on platformdirs; but `logging_config.py` logs to hand-rolled `~/.norefund/logs` (inconsistent — unify).
- GUI shell `gui/main_view.py`: adding a view = VIEW_* constant + `_TITLES` entry + `_make_view` branch + nav tuple in `_build_sidebar`. Sidebar footer says "⚠ 100% offline. No API calls made." and hardcodes `v0.1.0`.
- Threading pattern to copy from `gui/parser_view.py`: daemon `threading.Thread` + `self._schedule` (`after(0,...)` with `winfo_exists` guard) + `threading.Event` cancel.
- Reusable widgets: `ContextBar`, `StatPill`, `IconButton`, `ProviderBadge`, `ModelDropdownButton`, `bind_mousewheel`; theme tokens/ICONS in `gui/theme.py`; pure helpers in `gui/formatting.py`.
- `huggingface_hub` is imported directly but only a transitive dep — make explicit.
- `pyinstaller>=6.21` already in dev deps; no `.spec` exists.

---

## Phase A — Resource manager core (`core/paths.py`, `core/resources.py`)

### A.0 `core/paths.py` — packaging-safe path layer (used everywhere from now on)
```python
def bundled_resource(relpath: str) -> Path   # dev: src/norefund/<rel>; frozen: sys._MEIPASS/norefund/<rel>
def app_config_dir() -> Path                 # platformdirs user_config_dir("NoRefund", "PhantomVK")
def app_log_dir() -> Path                    # platformdirs user_log_dir
def app_data_dir() -> Path                   # platformdirs user_data_dir
def tiktoken_cache_dir() -> Path             # resolved TIKTOKEN_CACHE_DIR (see below)
def hf_cache_dir() -> Path                   # mirror huggingface_hub.constants.HF_HUB_CACHE
```
- `models_registry.py`: `_DEFAULT_REGISTRY_PATH` → `paths.bundled_resource("config/default_models.yaml")`.
- `logging_config.py`: `~/.norefund/logs` → `paths.app_log_dir()`; don't migrate old files, list legacy dir in Resources view if it exists. `paths` must import only stdlib+platformdirs (no cycles).
- `main.py` startup: if `TIKTOKEN_CACHE_DIR` unset, set it to `app_data_dir()/"tiktoken-cache"` **before** tiktoken use — tiktoken's default cache is in tempdir and gets wiped, which would make downloads silently vanish. Respect user-set env var.

### A.1 Dataclasses
```python
@dataclass(frozen=True)
class TokenizerResource:
    key: str                      # "tiktoken:o200k_base" / "hf:deepseek-ai/DeepSeek-V3"
    backend: Literal["tiktoken", "hf"]
    name: str
    model_ids: tuple[str, ...]
    is_cached: bool
    cache_path: Optional[Path]
    size_bytes: Optional[int]
    source_url: Optional[str]
    notes: Optional[str] = None   # e.g. "Gated repo — requires HF account/token"

@dataclass(frozen=True)
class ManagedDir:
    label: str; path: Path; exists: bool; size_bytes: int; file_count: int

@dataclass(frozen=True)
class ResourceReport:
    tokenizers: list[TokenizerResource]
    dirs: list[ManagedDir]
    total_tokenizer_bytes: int

class ResourceDownloadError(RuntimeError): ...
class DownloadCancelled(Exception): ...
```

### A.2 Enumeration (pure): `required_tokenizers(models) -> list[...]`
Dedupe by (backend, canonical name). tiktoken canonicalization: `tiktoken.encoding_name_for_model(name)` (pure dict lookup), `KeyError` → name is already an encoding. Current registry collapses to **5 resources**: `o200k_base` (gpt-4o/mini/4.1), `cl100k_base` (Claude/Gemini approx), and 3 HF repos (DeepSeek, Llama 3, Mistral).

### A.3 tiktoken cache probe — "capture, don't load"
tiktoken stores `cache_dir / sha1(blob_url).hexdigest()`; blob URLs live in constructor closures in `tiktoken_ext.openai_public.ENCODING_CONSTRUCTORS`. Probe: temporarily patch `tiktoken.load.read_file_cached` with a recorder that raises a private capture exception carrying `(blobpath, expected_hash)`, invoke the encoding constructor, catch. Then `is_cached = cache_file.exists()`, size via `stat()`. Fast (never parses vocab), never networks, stays correct if tiktoken changes URLs. Fallback on any failure: reuse existing `_load_tiktoken_offline_first` pattern for a bare `is_cached` bool (`cache_path=None`). Add a canary test that fails loudly if tiktoken internals (`read_file_cached`, `ENCODING_CONSTRUCTORS`) disappear; verify against pinned tiktoken version.

### A.4 HF cache probe
`hf_hub_download(repo_id, "tokenizer.json", local_files_only=True)` in try/except — same mechanism the loader uses, so probe always matches loader behavior. Size from resolved blob `stat()`; optionally enrich with `scan_cache_dir()` whole-repo `size_on_disk` (guarded). Statically mark gated repos (`meta-llama/*`). Promote `huggingface_hub` to an explicit dependency in `pyproject.toml`.

### A.5 Report assembly
`dir_stats(path) -> (bytes, file_count)` (rglob, tolerate per-file OSError); `build_resource_report(models=None) -> ResourceReport` covering config dir, log dir, legacy `~/.norefund/logs`, tiktoken cache, HF cache. May be slow on big HF caches — GUI must call off the UI thread.

### A.6 Downloads (the one sanctioned network path)
```python
ProgressFn = Callable[[int, Optional[int]], None]
def download_tokenizer(resource, *, on_progress=None, cancel_event=None) -> TokenizerResource
```
- **tiktoken** (determinate progress): stream captured blob URL via urllib in 64 KiB chunks → temp file in same cache dir → check cancel per chunk → verify sha256 against tiktoken's `expected_hash` → `os.replace` to `cache_file`. Writes exactly the file `read_file_cached` expects — existing offline loader picks it up unchanged.
- **HF** (indeterminate progress): `hf_hub_download(repo_id, "tokenizer.json")` without `local_files_only`; map `GatedRepoError`/HTTP errors to `ResourceDownloadError` with actionable text. Cancel is best-effort (abandon result).
- After success: new `tokenization.invalidate_tokenizer_cache()` clears `_tokenizer_cache` (incl. backends stuck in approximate-fallback mode) so downloads work without restart.
- Update CLAUDE.md core rule: "no network calls except `core/resources.download_tokenizer`, which runs only on explicit user action".

### A.8 Tests — `tests/test_resources.py`, `tests/test_paths.py`
Dedupe/canonicalization; tiktoken probe with `TIKTOKEN_CACHE_DIR=tmp_path` (miss → hit after planting file at `sha1(url)` name); HF probe with monkeypatched `hf_hub_download`; download happy path / sha mismatch / mid-stream cancel with fake urlopen (`io.BytesIO`); `dir_stats`; `bundled_resource(...).exists()`; tiktoken-internals canary.

**Files**: create `core/paths.py`, `core/resources.py`, 2 test files; modify `models_registry.py`, `tokenization.py`, `logging_config.py`, `main.py`, `pyproject.toml`, `CLAUDE.md`.

---

## Phase B — Resources GUI view

**Files**: create `gui/resources_view.py`; modify `gui/main_view.py` (4-step view registration, "Data" nav section), `gui/theme.py` (add `download` icon glyph — verify rendering in resolved UI font), `gui/formatting.py` (add pure `fmt_bytes(n: Optional[int]) -> str` + tests).

Layout (`CTkScrollableFrame` + `bind_mousewheel`, card style like registry_view):
- **Header**: `StatPill`s — "N of M downloaded", total tokenizer disk usage; refresh button.
- **Tokenizers section**: per-resource row — status dot (cached/missing/error), name + backend badge, "used by N models" sublabel, size (`fmt_bytes`), truncated `cache_path` in mono font, actions: Download (primary `IconButton`) → swaps to `CTkProgressBar` (determinate tiktoken / indeterminate HF) + cancel; Open folder when cached. Gated-repo errors show inline with "open page ↗" (`webbrowser.open`).
- **Storage section**: per `ManagedDir` — label, path, size, file count, Open folder (`os.startfile` / `open` / `xdg-open`).

Behavior: initial scan and refresh on daemon thread with "Scanning…" state, delivered via copied `_schedule` helper; one download at a time (other buttons disabled); on success refresh row + totals and rely on `invalidate_tokenizer_cache` so Parser works immediately.

Sidebar footer: replace "⚠ 100% offline. No API calls made." with "✓ Local analysis. Your files never leave this machine."

Manual verify checklist: nothing-cached and all-cached states, download success then immediate Parser use, cancel mid-download, gated repo failure, open-folder, close app mid-download (clean exit), theme toggle while open.

---

## Phase C — Copy & docs repositioning

Message: **"Desktop-first, privacy-respecting. Analysis is 100% local — your documents never leave your machine. Network is used only when you explicitly download a tokenizer."**

Grep `offline|100%|API calls` repo-wide. Modify:
- `README.md`: tagline, "Why" section, "Staying fully offline" section → "Tokenizer downloads" (describe Resources view + cache locations), feature list.
- `CLAUDE.md`: project description line + finalized network rule (from A).
- `core/tokenization.py`: error hints → "Open the Resources view in NoRefund to download it (one click)" (keep CLI one-liner as secondary for headless); docstrings ("OFFLINE-FIRST" → "local-only loading").
- `gui/` strings + `default_models.yaml` comments; update tests asserting on old hint text (`test_tokenization.py`).

Done when: full `pytest` passes and `grep -ri "100% offline"` finds nothing.

---

## Phase D — Cost/compare workflows

### Core: `core/compare.py`, `core/export.py`
- `ModelComparison` dataclass (per-model tokens, context fit, input/output/total cost, `output_tokens` what-if assumption, `tokenizer_is_approximate`, `error`); `CompareReport` (source label, results — error rows included, never raises).
- `compare_text(text, models, output_tokens)`, `compare_paths(paths, models, output_tokens, *, on_progress, cancel_event)`, pure `what_if(result, output_tokens, model)` recompute.
- **Efficiency contract**: group models by tokenizer key (reuse A.2 canonicalization), call `count()` once per unique tokenizer per text, fan out via existing pure `costing.py` functions. Missing tokenizer → error row with "download in Resources" hint. Folder mode: extract each file once, aggregate per tokenizer.
- `export.py`: pure string builders, no I/O — `comparison_to_csv/markdown(report)`, `analysis_results_to_csv/markdown(results)` (`csv.writer` on StringIO; GitHub-table Markdown with `~` approximate marker and header noting assumptions).

### GUI: new **Compare** view + export buttons on Parser
- `gui/compare_view.py` in "Tools" nav: input card (paste text / pick file / pick folder), model multi-select (`ModelCheckList` — new small widget in `widgets.py`, all checked by default), output-tokens entry (default from settings; changing it recomputes via `what_if` instantly, no re-tokenization). Results grid sorted by total cost, cheapest highlighted; columns: model, tokens (~), context %, fits/chunks, input $, output $, total $. Export CSV/MD via `filedialog.asksaveasfilename`. Worker thread + `_schedule` + cancel.
- `gui/parser_view.py`: add Export CSV / Export MD buttons for current results.

### Tests
`test_compare.py`: tokenize-once (fake tokenizer counts `count()` calls per key), error rows, `what_if` math, folder aggregation. `test_export.py`: golden strings (comma quoting, approx marker, empty results).

---

## Phase E — Polish & first-run

- **First-run banner**: `Settings.onboarding_dismissed: bool = False`; on shell build, worker-thread check `any(r.is_cached ...)`; if nothing cached and not dismissed, non-modal `NoticeBanner` (new widget): "No tokenizers downloaded yet — counts will be rough approximations → Open Resources"; dismiss persists. Resources view gets a "Download all" convenience button (serial queue).
- **Drag & drop**: `tkinterdnd2` as *optional* dependency (`[project.optional-dependencies] dnd`); new `gui/dnd.py` with `enable_file_drop(widget, on_paths) -> bool` (no-op False when lib missing; parses Tcl brace-quoted path lists). `gui/app.py` root switches to `ctk.CTk` + `TkinterDnD.DnDWrapper` mixin only when import succeeds. Drop targets: Parser file area, Compare input card; filter by supported suffixes.
- **Misc**: Tooltip widget (truncated paths, "used by N models"); Ctrl+1..5 view switching, Escape cancels active work; version single-sourcing — sidebar footer reads `importlib.metadata.version("norefund")` with frozen-safe fallback constant.
- Tests: settings round-trip; DnD path-list parsing (names with spaces); manual: app launches without tkinterdnd2, banner shows only when nothing cached, dismiss persists.

---

## Phase F — Packaging readiness (design only, no installers now)

- **Audit**: all read-only resources via `paths.bundled_resource()`; all writable state via platformdirs; no `__file__`/cwd/`sys.argv[0]` assumptions; `TIKTOKEN_CACHE_DIR` set before tiktoken imports.
- **PyInstaller spec outline** (documented, built later as `packaging/norefund.spec`): one-dir windowed build; `datas`: registry YAML + `collect_data_files("customtkinter")` (+ tkinterdnd2 if bundled); `hiddenimports`: **`tiktoken_ext`, `tiktoken_ext.openai_public`** (classic failure — plugin discovery invisible to static analysis).
- **Per-OS targets** (record now, build later): Windows → Inno Setup .iss, per-user install, Start-menu shortcut; macOS → .app + create-dmg, notarization noted; Linux → AppImage (fallback tarball + .desktop).
- **Do NOT bundle tokenizer caches** — size/licensing/staleness; the Resources view + first-run banner are the post-install acquisition story.

---

## Order & shippability

| Phase | Ships alone? | Depends on |
|---|---|---|
| A resources core + paths | yes | — |
| B Resources view | yes | A |
| C copy/docs | yes | B (wording references Resources view) |
| D compare/export | yes | A |
| E polish/first-run/DnD | yes | B |
| F packaging design doc | yes | A |

## Verification

- Per CLAUDE.md: core changes covered by pure unit tests (`pytest`); GUI changes manually verified — no crash, clean close, edge cases (nothing cached, cancel mid-download, missing optional deps).
- End-to-end after A+B: fresh machine simulation (`TIKTOKEN_CACHE_DIR`+`HF_HOME` → empty tmp dirs), open Resources, download `o200k_base`, run Parser on a PDF with gpt-4o — exact counts, no restart.
- After C: `grep -ri "100% offline"` returns nothing; `ruff check src/` clean.

## Critical files
- `src/norefund/core/tokenization.py` — offline-block pattern to reuse; hints to reword; add `invalidate_tokenizer_cache()`
- `src/norefund/core/models_registry.py` — enumeration source; path helper migration
- `src/norefund/gui/main_view.py` — view registration recipe; footer copy; banner host
- `src/norefund/gui/parser_view.py` — threading/`_schedule`/cancel pattern to copy; export buttons
- `src/norefund/logging_config.py` — log-dir unification
