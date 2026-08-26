# Adding a Model

Adding a model to NoRefund is a YAML entry, not a code change. This is the single
highest-volume contribution the project gets, so this doc walks through exactly what
each field means and where the numbers come from. See [Data Sources](DATA_SOURCES.md)
for the broader accuracy discipline this feeds into.

## Which file(s) you need

| You're adding... | Edit |
|---|---|
| A hosted API model (OpenAI, Anthropic, Google, DeepSeek, ...) | [`config/default_models.yaml`](../src/norefund/config/default_models.yaml) only |
| A self-hostable open-weight model (Llama, Qwen, Mistral, ...) | Both [`config/default_models.yaml`](../src/norefund/config/default_models.yaml) and [`config/model_architectures.yaml`](../src/norefund/config/model_architectures.yaml) |

`model_architectures.yaml` is only for models the Self-Host Fit Check needs to reason
about VRAM for. A hosted-only model (nobody runs GPT-5.6 on their own GPU) never needs
an entry there.

## `default_models.yaml`: field by field

```yaml
- id: openai:gpt-5.6-sol           # provider:slug, lowercase, used everywhere as the model's identity
  display_name: "GPT-5.6 Sol"      # shown in the UI
  provider: "OpenAI"
  tokenizer_backend: "tiktoken"    # "tiktoken" or "hf" (HuggingFace) — see below
  tokenizer_name: "gpt-4o"         # tiktoken encoding name, or an HF repo id
  context_window: 1050000          # max input tokens the model accepts
  input_price_per_million: 4.00
  output_price_per_million: 20.00
  currency: "USD"
  docs_url: "https://developers.openai.com/api/docs/pricing"
  pricing_verified_on: "2026-08-26"  # the date you actually read docs_url, not today's date by default
```

Optional fields:

- **`tokenizer_is_approximate: true`** — set this when the provider doesn't publish a
  downloadable tokenizer, so NoRefund falls back to a close-but-not-exact stand-in
  (currently `cl100k_base` for Anthropic and Google models). Omit it entirely for an
  exact tokenizer; don't set it to `false`.
- **`long_context_threshold` / `long_context_input_price_per_million` /
  `long_context_output_price_per_million`** — some providers charge a higher rate once a
  request crosses a token threshold (see [Mathematics](MATHEMATICS.md) for the exact
  formula). Add all three together or none of them.
- **`pricing_note`** — free-text, for anything the flat per-million fields can't capture
  (e.g. an off-peak discount). See the `deepseek:deepseek-v4-flash` entry for an example.

Self-hosted open-weight models still get an entry here, priced at
`input_price_per_million: 0.00` / `output_price_per_million: 0.00` (nobody pays a
per-token API fee to run their own weights), and `pricing_verified_on` is omitted since
there's no vendor price to verify.

### `tokenizer_backend: tiktoken` vs `hf`

- **`tiktoken`** — for models whose real tokenizer is one of `tiktoken`'s built-in
  encodings (OpenAI's own models, or another provider using the same encoding
  intentionally or as an approximation). `tokenizer_name` is the encoding name, e.g.
  `gpt-4o` or `cl100k_base`.
- **`hf`** — for models with a tokenizer published on HuggingFace. `tokenizer_name` is
  the HF repo id, e.g. `Qwen/Qwen2.5-7B-Instruct`. NoRefund downloads the tokenizer's
  vocab files on first use (see [Data Sources](DATA_SOURCES.md#tokenizer-downloads)).

### If the official HF repo is gated

Some model families require a license click-through before HuggingFace lets you fetch
`config.json` or the tokenizer at all, which breaks the tokenizer download for anyone
without an accepted license. If an ungated mirror exists, point `tokenizer_name` at that
instead, but only after verifying the mirror is genuinely identical, not just similarly
named. See [Data Sources → Verifying licence-gated mirrors](DATA_SOURCES.md#verifying-licence-gated-mirrors)
for the exact git-blob-oid check, and the existing `meta:llama-*` and `google:gemma-2-*`
entries for real examples of the comment style this needs (which mirror, which file, and
the oid you compared).

## `model_architectures.yaml`: field by field

Only needed for self-hostable models. Every number here comes from the model's
published HuggingFace `config.json`, cross-checked where noted:

```yaml
- id: qwen:qwen2.5-7b              # must match the id in default_models.yaml
  display_name: "Qwen2.5 7B"
  family: "Qwen 2.5"
  vendor: "Qwen"
  total_params: 7620000000         # cross-check against the HF safetensors API total, not a rounded model-card number
  active_params: 7620000000        # differs from total_params only for mixture-of-experts models
  n_layers: 28
  n_attention_heads: 28
  n_kv_heads: 4                    # the GQA key/value head count — smaller than n_attention_heads; do not confuse the two
  head_dim: 128                    # copy from config.json directly; it is not always hidden_size / n_attention_heads
  hidden_size: 3584
  max_context_length: 131072
  attention_type: "gqa"            # "gqa" or "mla"
  docs_url: "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct"
```

MLA models (DeepSeek's architecture) also need `kv_lora_rank` and `qk_rope_head_dim` —
see the `deepseek:deepseek-v3` entry. Sliding-window models (Gemma 2's architecture)
also need `sliding_window` and `sliding_window_pattern` — see the `google:gemma-2-*`
entries and `core/selfhost.py`'s `kv_cache_bytes` for how the pattern is used.

**Getting `total_params` right matters**: it drives the weight-memory estimate in the
Self-Host Fit Check. Don't trust a model card's rounded figure; cross-check against
`GET /api/models/{repo}?blobs=true`'s `safetensors.total` field.

## Verifying your entry

```bash
pytest tests/test_registry_data.py
```

This confirms the two files agree with each other (matching ids, consistent shared
fields) and that every priced entry has a `pricing_verified_on` date. It cannot confirm
the price itself is still correct — only re-reading the vendor's page can, which is why
`pricing_verified_on` exists as an honesty marker rather than a formality.

## Opening the PR

One model (or one fix) per PR is easiest to review. Use `type:docs` if you're only
touching these YAML files with no code change, and `area:registry-data`. See
[Contributing](CONTRIBUTING.md) for branch naming, commit style, and the PR template.
