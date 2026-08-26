# NoRefund

> **Know before you run. Because APIs don't care about your feelings.**

NoRefund is a free, open-source, desktop-first utility for AI engineers.
It counts tokens in documents (PDF, PPTX, DOCX, TXT, MD, etc.) and estimates the cost
of running them through any major LLM — before you make a single API call.

---

## Why NoRefund?

APIs charge you the moment tokens run. No refund, no mercy.
NoRefund tells you exactly how many tokens your document will consume, whether it fits in
a model's context window, and what it will cost.

Analysis is 100% local — your documents never leave your machine. Network access is
used only when you explicitly download a tokenizer, from the app's Resources view.

---

## Features

- Parse PDF, PPTX, DOCX, TXT, MD files
- Count tokens for 21 models across 7 providers (OpenAI, Anthropic, Google, DeepSeek,
  Meta, Mistral, Qwen)
- Context window usage percentage with fit/chunk analysis
- Compare cost and context fit across multiple models side by side, with per-model and
  portfolio cost projection
- Self-Host Fit Check: estimate whether an open-weight model actually fits on your own
  GPU, Apple Silicon Mac, or cloud instance, given quantization, KV cache precision,
  context length, and concurrency
- Local cost estimation per model, with no data ever sent anywhere
- Model Registry: browse every supported model's context window, pricing, and
  architecture details
- Resources view: see which tokenizers are downloaded, where they live on disk, and
  their size, with a one-click download for anything missing
- CLI and a native desktop app (React + pywebview) for Windows, macOS, and Linux

---

## Download

Prebuilt Windows, macOS, and Linux builds are on the
[Releases page](https://github.com/Phantom-VK/NoRefund/releases) — no Python install
required.

**Windows SmartScreen:** NoRefund isn't code-signed (a signing certificate costs money
this free project doesn't have), so Windows shows a "Windows protected your PC" warning
the first time you run it. Click **More info → Run anyway** to continue. This warning
means the publisher isn't verified, not that the app is unsafe — the source is right
here in this repo.

**macOS Gatekeeper:** for the same reason, macOS may refuse to open the app with an
"is damaged and can't be opened" dialog. Run `xattr -cr NoRefund.app` in Terminal after
extracting it — see `packaging/README.md` for details.

---

## Quick Start

```bash
# Install
pip install -e ".[dev]"
cd frontend && npm install && npm run build && cd ..

# CLI
norefund path/to/file.pdf --model openai:gpt-4o

# Desktop app
norefund --gui
```

For frontend development with hot reload, see `CLAUDE.md`'s Commands section.

---

## Project Structure

```
src/norefund/
  main.py              # CLI entry point + GUI launch
  desktop/             # pywebview shell and JS bridge (api.py, app.py, dto.py, jobs.py)
  core/
    parsing.py         # Document text extraction
    tokenization.py    # Tokenizer backends
    costing.py         # Cost & context calculations
    models_registry.py # Model/pricing config
    service.py         # Orchestration
  config/
    default_models.yaml  # Local model registry
frontend/               # React UI (Calculator, Parser, Compare, Fit Check, Registry, Resources)
tests/
```

---

## Supported Models

21 models across 7 providers — OpenAI, Anthropic, Google, DeepSeek, Meta, Mistral, and
Qwen, spanning both hosted API models and self-hosted open-weight models. The
in-app **Model Registry** view is the source of truth for the current list, context
windows, and pricing (`config/default_models.yaml` backs it, so it never drifts from
what the app actually uses).

**Tokenizer accuracy:** OpenAI models, DeepSeek V3, Llama, Qwen, and Mistral use each
provider's real tokenizer. Anthropic and Google don't publish a local tokenizer for
Claude or Gemini, so those counts are a `cl100k_base` approximation — the app marks
them `(approx.)` wherever they're shown.

**Tokenizer downloads:** the first time you use a given tokenizer, NoRefund needs its
vocab files cached locally (one-time, requires internet). Open the **Resources** view
in the app to see what's downloaded, where it's stored on disk, how much space it
takes, and to download anything missing with one click. Once cached, NoRefund never
touches the network again for that tokenizer. If it isn't cached yet, NoRefund raises
a clear error pointing you to the Resources view instead of silently downloading it.

---

## License

MIT — see [LICENSE](LICENSE)
