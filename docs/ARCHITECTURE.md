# Architecture

NoRefund is three layers, each with one job, talking to each other in one direction only:

```
frontend/  (React UI)
    │  calls window.pywebview.api.<method>()
    ▼
desktop/   (pywebview shell + JS bridge)
    │  calls plain functions, gets dataclasses back
    ▼
core/      (pure logic: parsing, tokenizing, costing, self-host math)
```

`core/` never imports from `desktop/` or `frontend/`, and `desktop/` never contains
business logic — it only marshals arguments in and results out. This split is why every
calculation in the app is unit-testable without a GUI: see
[Mathematics](MATHEMATICS.md) for what those calculations actually compute.

## `core/` — pure logic

Every module here is a set of plain functions and [dataclasses](https://docs.python.org/3/library/dataclasses.html) —
no side effects, no network calls (with two explicit, user-triggered exceptions below),
no filesystem writes except through [`core/paths.py`](../src/norefund/core/paths.py).
This is deliberate: a function that only transforms its arguments into a return value can
be tested with a plain `assert`, no mocking required.

| Module | Responsibility |
|---|---|
| [`parsing.py`](../src/norefund/core/parsing.py) | Extract plain text from PDF/PPTX/DOCX/TXT/MD |
| [`tokenization.py`](../src/norefund/core/tokenization.py) | Tokenizer backends (tiktoken, HuggingFace) — one per model family |
| [`costing.py`](../src/norefund/core/costing.py) | Cost & context-window math ([details](MATHEMATICS.md#cost-tiered-pricing)) |
| [`selfhost.py`](../src/norefund/core/selfhost.py) | VRAM-fit math for self-hosting ([details](MATHEMATICS.md#self-host-fit-does-this-model-fit-on-my-hardware)) |
| [`quantization.py`](../src/norefund/core/quantization.py) | Bits-per-weight / KV-cache-bytes-per-element constant tables |
| [`compare.py`](../src/norefund/core/compare.py) | Multi-model comparison for one document or piece of text |
| [`portfolio.py`](../src/norefund/core/portfolio.py) | Business-volume cost projection (calls/month → $/month) |
| [`service.py`](../src/norefund/core/service.py) | Orchestrates parsing → tokenizing → costing for a single analysis |
| [`export.py`](../src/norefund/core/export.py) | Pure string builders for CSV/Markdown export |
| [`report/`](../src/norefund/core/report/) | PDF/HTML report rendering, both built from one shared `ReportModel` |
| [`models_registry.py`](../src/norefund/core/models_registry.py) | Loads/queries `config/default_models.yaml` |
| [`architectures.py`](../src/norefund/core/architectures.py) | Loads/queries `config/model_architectures.yaml` |
| [`hardware_registry.py`](../src/norefund/core/hardware_registry.py) | Loads/queries `config/hardware.yaml` |
| [`resources/`](../src/norefund/core/resources/) | Tokenizer cache inventory — what's downloaded, where, how big |
| [`currency.py`](../src/norefund/core/currency.py) | USD → display-currency conversion |
| [`settings.py`](../src/norefund/core/settings.py) | User preferences, persisted as JSON |
| [`secrets.py`](../src/norefund/core/secrets.py) | API tokens (e.g. HuggingFace), stored via the OS keychain — never in settings.json |
| [`paths.py`](../src/norefund/core/paths.py) | Packaging-safe path resolution (bundled resources vs. platform data/config/log dirs) |

**The only network calls anywhere in `core/`** are
[`resources.download_tokenizer()`](../src/norefund/core/resources/download.py) and
[`currency.fetch_exchange_rates()`](../src/norefund/core/currency.py) — both run only
when a user explicitly clicks a "Download" or "Refresh rates" button. This is the
technical backbone of the "your documents never leave your machine" claim: nothing else
in the codebase can reach the network at all.

## `desktop/` — the pywebview shell and JS bridge

| Module | Responsibility |
|---|---|
| [`app.py`](../src/norefund/desktop/app.py) | Window creation and lifecycle |
| [`api.py`](../src/norefund/desktop/api.py) | The `js_api` bridge — one method per use case, reachable from JS as `window.pywebview.api.<name>` |
| [`dto.py`](../src/norefund/desktop/dto.py) | Converts `core/` dataclasses into JSON-safe structures |
| [`jobs.py`](../src/norefund/desktop/jobs.py) | Background job tracking (progress, cancellation, results) for long-running analyses |

### The bridge contract

Every `Api` method in `api.py` is wrapped with `@_guard`, so an exception raised inside
`core/` reaches JavaScript as a structured `{ok: False, error}` object instead of an
opaque promise rejection — [`frontend/src/lib/bridge.ts`](../frontend/src/lib/bridge.ts)
unwraps this envelope so React views never have to think about it; they just get a
result or throw.

Results cross the bridge through [`dto.to_jsonable()`](../src/norefund/desktop/dto.py),
which recursively walks a `core/` dataclass and turns it into plain dicts/lists/strings
that `json.dumps` accepts. Field **names are preserved exactly** — the TypeScript
interfaces in [`frontend/src/lib/types.ts`](../frontend/src/lib/types.ts) mirror every
Python dataclass one field at a time. Nothing enforces this match at compile time, so a
contract test — `test_dataclass_fields_match_ts_interface` in
[`tests/test_desktop_api.py`](../tests/test_desktop_api.py) — parses both sides and
fails the build if they drift. **If you add or rename a field on a `core/` dataclass
that crosses the bridge, you must update the matching TypeScript interface in the same
change, or this test will fail.**

## `frontend/` — the React UI

Owns all presentation: formatting, colour thresholds, labels, sort order, empty states.
It never computes a cost or a fit verdict from scratch — with one deliberate exception:

| Path | Responsibility |
|---|---|
| [`src/lib/bridge.ts`](../frontend/src/lib/bridge.ts) | The only file where `any` is allowed — the JS side of the bridge boundary |
| [`src/lib/types.ts`](../frontend/src/lib/types.ts) | TypeScript mirror of every `core/` dataclass that crosses the bridge |
| [`src/lib/costing.ts`](../frontend/src/lib/costing.ts) | **The one sanctioned duplication of `core/` logic** — lets the Calculator view recompute cost live as you type, without a bridge round-trip per keystroke. Kept in parity with `costing.py` by [`costing.test.ts`](../frontend/src/lib/costing.test.ts) |
| [`src/views/`](../frontend/src/views/) | One folder per feature: Calculator, Parser, Compare, FitCheck, Registry, Resources |
| [`src/components/app/`](../frontend/src/components/app/) | App-specific composite components (Sidebar, Header, ModelSelect, ProcessingDialog, …) |
| [`src/components/ui/`](../frontend/src/components/ui/) | Low-level primitives (button, dialog, table, tabs, …) |
| [`src/hooks/`](../frontend/src/hooks/) | `useJob`, `useBridge`, `useSettings`, `useTheme`, … |

## End-to-end: analyzing one file

1. User drops a file onto the Parser view → `frontend` calls
   `window.pywebview.api.analyze_file(path, model_id)`.
2. `desktop/api.py`'s `Api.analyze_file` (wrapped in `@_guard`) calls
   `core/service.py`'s orchestration function.
3. `service.py` calls `core/parsing.extract_text()`, then
   `core/tokenization`'s backend for the chosen model, then `core/costing.py`'s
   functions — all pure, all synchronous.
4. The resulting `AnalysisResult` dataclass goes through `dto.to_jsonable()` and back
   across the bridge as JSON.
5. `frontend/src/lib/bridge.ts` unwraps the `{ok, error}` envelope; the view renders the
   typed result.

For a document large enough to need chunking, or a batch of files, the same core call
runs inside a **background job** ([`desktop/jobs.py`](../src/norefund/desktop/jobs.py))
so the UI can show progress and support cancellation instead of blocking on one long
`js_api` call.
