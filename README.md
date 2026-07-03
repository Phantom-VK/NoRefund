# NoRefund

> **Know before you run. Because APIs don't care about your feelings.**

NoRefund is a free, open-source, offline-first desktop utility for AI engineers.
It counts tokens in documents (PDF, PPTX, DOCX, TXT, MD, etc.) and estimates the cost
of running them through any major LLM — before you make a single API call.

---

## Why NoRefund?

APIs charge you the moment tokens run. No refund, no mercy.  
NoRefund tells you exactly how many tokens your document will consume, whether it fits in
a model's context window, and what it will cost — all 100% offline.

---

## Features (v0.1)

- Parse PDF, PPTX, DOCX, TXT, MD files
- Count tokens for 10+ LLM models (GPT-4o, Claude, Gemini, DeepSeek, Llama, Mistral)
- Context window usage percentage with fit/chunk analysis
- Offline cost estimation per model
- CLI and Desktop GUI (CustomTkinter)

---

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# CLI
norefund path/to/file.pdf --model openai:gpt-4o

# GUI
norefund --gui
```

---

## Project Structure

```
src/norefund/
  main.py              # Entry point
  gui/                 # CustomTkinter GUI
  core/
    parsing.py         # Document text extraction
    tokenization.py    # Tokenizer backends
    costing.py         # Cost & context calculations
    models_registry.py # Model/pricing config
    service.py         # Orchestration
  config/
    default_models.yaml  # Offline model registry
tests/
```

---

## Supported Models (offline)

| Model | Provider | Context Window |
|---|---|---|
| GPT-4o | OpenAI | 128K |
| GPT-4o Mini | OpenAI | 128K |
| GPT-4.1 | OpenAI | 1M |
| Claude 3.5 Sonnet | Anthropic | 200K |
| Claude 3 Haiku | Anthropic | 200K |
| Gemini 2.0 Flash | Google | 1M |
| Gemini 1.5 Pro | Google | 2M |
| DeepSeek V3 | DeepSeek | 128K |
| Llama 3 8B | Meta (self-hosted) | 8K |
| Mistral 7B | Mistral (self-hosted) | 32K |

**Tokenizer accuracy:** OpenAI models, DeepSeek V3, Llama 3, and Mistral use each
provider's real tokenizer. Anthropic and Google don't publish a local tokenizer for
Claude or Gemini, so those counts are a `cl100k_base` approximation — the app marks
them `(approx.)` wherever they're shown.

**Staying fully offline:** the first time you use a given tokenizer, NoRefund needs to
cache its vocab files locally (one-time, requires internet). After that it never
touches the network again for that model. If a tokenizer isn't cached yet, NoRefund
raises a clear error with the exact command to run, instead of silently downloading it.

---

## License

MIT — see [LICENSE](LICENSE)
