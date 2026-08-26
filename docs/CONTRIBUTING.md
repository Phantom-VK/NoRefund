# Contributing

How to set up NoRefund for development, the conventions this repo follows, and how to
open a PR that's easy to review.

## Dev setup

```bash
pip install -e ".[dev]"
cd frontend && npm install && cd ..

# Terminal 1 — Vite dev server with hot reload
cd frontend && npm run dev

# Terminal 2 — the desktop app, pointed at the dev server
NOREFUND_DEV=1 python -m norefund.desktop.app
```

For a production-shaped build instead:

```bash
cd frontend && npm run build && cd ..
python -m norefund.desktop.app
```

## Running checks before you push

```bash
pytest                          # Python test suite
cd frontend && npm test         # Frontend test suite
ruff check src/                 # Python lint
```

All three run in CI on every PR ([`ci.yml`](../.github/workflows/ci.yml),
[`build.yml`](../.github/workflows/build.yml)) — run them locally first so review
feedback is about the change itself, not a lint error.

## Coding conventions

- **`core/` stays pure.** No side effects, no I/O, no network calls except the two
  explicit user-triggered exceptions (`resources.download_tokenizer`,
  `currency.fetch_exchange_rates` — see [Architecture](ARCHITECTURE.md#core--pure-logic)).
  This is what makes every calculation unit-testable without a GUI or a mock.
- **Type hints everywhere**, `from __future__ import annotations` in every new Python
  file.
- **Dataclasses for structured data** (`ModelInfo`, `AnalysisResult`, `Settings`, …) —
  not raw dicts.
- **`desktop/` only marshals.** Argument in, `core/` call, DTO out — no business logic
  belongs there. See [Architecture](ARCHITECTURE.md#desktop--the-pywebview-shell-and-js-bridge)
  for the bridge contract, including the dataclass ↔ TypeScript field-matching rule.
- **TypeScript `strict` is on.** `any` is allowed only at the bridge boundary in
  `frontend/src/lib/bridge.ts`.
- **Keep it simple.** For scenarios
  that can't happen don't add abstractions, error handling, or config. DO NOT OVER ENGINEER! Three similar lines beat a premature helper. Do check the real edge
  cases (empty file, zero context window, missing tokenizer cache) — see
  [Definition of Done](#definition-of-done) below.

## Branch naming

`<user_name><type>/<short-description>`, matching this repo's actual history:

```
vikram/feat/portfolio-projection
vikram/fix/dropdown-cross-os
vikram/chore/gui-cleanup
vikram/ref/code-cleanup
```

`type` is one of: `feat`, `fix`, `chore`, `ref` (refactor), `test`, `docs`, `ci`, `build`.

## Commit messages

`type(scope): imperative, present-tense summary` — scope is usually the module or
feature touched. Real examples from this repo's history:

```
fix(selfhost): account for Gemma 2's sliding-window attention in KV cache sizing
feat(costing): support context-tiered pricing in the model registry
test(config): add registry cross-consistency checks and price verification dates
```

Never add an AI co-author line, even if an AI assistant helped write the change.

## Tests

- **Logic changes** (`core/`: parsing, tokenization, costing, self-host, registries):
  add or update a pure-function unit test in the matching `tests/test_*.py` file — see
  [Project Structure](PROJECT_STRUCTURE.md#tests) for the module → test-file mapping.
  No GUI or filesystem mocking should be needed for something like `costing.py`.
- **Bridge changes** (a `core/` dataclass gaining/renaming a field that crosses to JS):
  update the matching interface in `frontend/src/lib/types.ts` in the same PR, or
  `test_dataclass_fields_match_ts_interface` in
  [`tests/test_desktop_api.py`](../tests/test_desktop_api.py) will fail.
- **UI changes** (`frontend/`, `desktop/`): add a frontend test where reasonable, and
  manually verify in a running dev build (see [Dev setup](#dev-setup)).

## Definition of Done

Before calling a change finished:

1. The relevant test suite passes (`pytest`, or `npm test` for frontend changes).
2. The app still starts and doesn't crash — verify with a real run, not just tests.
3. The app can still close cleanly.
4. Edge cases don't raise uncaught exceptions: an empty file, a zero-length context
   window, a missing tokenizer cache, `None`/missing optional fields.
5. `ruff check src/` is clean.

## Opening a PR

1. Branch off `main` using the naming convention above.
2. Keep the PR focused — one logical change. A bug fix doesn't need an accompanying
   refactor.
3. Fill in the [PR template](../.github/PULL_REQUEST_TEMPLATE.md) — it auto-populates
   when you open a PR on GitHub.
4. Don't reference internal planning/handoff files, session notes, or AI-assistant
   artifacts in the PR description — describe the change and why, as if for a human
   reviewer with no other context.

### Worked example

Say you're fixing a rounding edge case in `context_usage_pct` when `context_window` is
negative rather than zero.

**Branch:** `fix/costing-negative-context-window`

**The change:** in [`core/costing.py`](../src/norefund/core/costing.py), extend the
existing `context_window <= 0` guard to also cover negative values it hadn't been tested
against (it already does, actually — but imagine it didn't).

**Test added**, in `tests/test_costing.py`:

```python
def test_context_usage_pct_returns_none_for_negative_context_window():
    assert context_usage_pct(100, -1) is None
```

**Commit:**

```
fix(costing): return None for negative context windows

context_usage_pct only guarded context_window == 0; a negative value
(shouldn't happen from the registry, but defensive here) fell through to
a nonsensical negative percentage instead of the "unknown" sentinel.
```

**PR title:** `fix(costing): return None for negative context windows`

**PR body:**

```markdown
## Summary
`context_usage_pct` returned a nonsensical negative percentage instead of
`None` when given a negative `context_window`, instead of matching the
existing zero-window behavior.

## Why
Found while reviewing costing.py's guards — the zero case was handled but
negative wasn't, even though both should mean "no valid window."

## Testing
- Added `test_context_usage_pct_returns_none_for_negative_context_window`
- `pytest tests/test_costing.py` passes
```
