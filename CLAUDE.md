# CLAUDE.md

NoRefund: desktop-first, privacy-respecting tool that counts tokens in local files (PDF/PPTX/DOCX/TXT) against real tokenizers, checks context-window fit, estimates LLM cost. Analysis is 100% local — your documents never leave your machine. Network is used only when you explicitly download a tokenizer (Resources view). Built because uploading huge decks to online counters is impractical and leaks data.

## Commands
```
pip install -e .
python -m norefund.gui.app     # run GUI
pytest                          # run tests
ruff check src/                 # lint
```

## Directory Purpose
- `core/` — pure logic, no GUI imports. No network calls except `core/resources.download_tokenizer`, which only runs on explicit user action (Resources view "Download" button)
- `core/resources.py` — tokenizer/cache inventory: what's downloaded, where, how big; the one sanctioned network path
- `core/paths.py` — packaging-safe path resolution (bundled resources, platformdirs data/config/log dirs)
- `core/secrets.py` — API tokens/secrets (e.g. HuggingFace token), stored via OS keychain (`keyring`), never in settings.json
- `core/parsing.py` — extract_text() per file type
- `core/tokenization.py` — TokenizerBackend impls (tiktoken, HF)
- `core/costing.py` — pure cost/context math, no I/O
- `core/service.py` — orchestrates parsing → tokenizing → costing
- `config/default_models.yaml` — model context windows + prices
- `gui/` — CustomTkinter views, delegate logic to `core/`

## Coding Conventions

- Keep code simple, readable and modular.
- Type hints everywhere; use `from __future__ import annotations` in every new file.
- Dataclasses for structured data (`ModelInfo`, `AnalysisResult`, `Settings`) — not raw dicts.
- Pure functions in `core/costing.py` — no side effects, no I/O, fully unit-testable.
- Prefer explicit `Optional[X]` over sentinel values (`-1`, `0`, `""`) for "no data" states.
- Keep GUI files focused on layout/wiring; delegate all computation to `core/`.
- 
## Issue Resolution
- Logic issues (core/): fix + unit test must pass + verify GUI doesn't crash
- GUI issues (gui/): fix + manually verify: (1) no crash, (2) closes clean, (3) edge cases handled
- Unknown: gather scope first (Scenario 2), then execute per above

## Testing / Definition of Done
- Any change to `core/` (parsing, tokenization, costing, service) should be verifiable with a pure-function unit test — no GUI or file-system mocking required for `costing.py`.
- Before considering a fix "done," manually verify: (1) the GUI doesn't crash, (2) the app can still close cleanly, (3) `None`/edge-case inputs (empty file, zero context window, missing tokenizer cache) don't raise uncaught exceptions.
