# Mathematics

Every number NoRefund shows you — a token count, a cost, a "does this fit on my GPU"
verdict — comes from a small set of pure functions in [`core/`](../src/norefund/core/).
"Pure" means: no I/O, same inputs always give the same output, and every one of them is
unit-tested without needing a GUI, a network call, or a mocked filesystem. This page
explains what each formula answers and why it's built the way it is. For the *data* that
feeds these formulas (prices, context windows, architecture parameters), see
[Data Sources](DATA_SOURCES.md) — this page is only about the calculations themselves.

## Token counting

NoRefund doesn't estimate token counts — it runs the same tokenizer the model provider
uses (tiktoken for OpenAI, a HuggingFace `tokenizers` backend for Llama/Qwen/Mistral/
DeepSeek). The only exception is Claude and Gemini, which don't publish a downloadable
tokenizer; those counts fall back to an approximation, always labeled `(approx.)` in the
UI — see [Data Sources](DATA_SOURCES.md#tokenizer-accuracy) for which models this
applies to. See [`core/tokenization.py`](../src/norefund/core/tokenization.py).

## Context window fit

| Question | Formula | Source |
|---|---|---|
| What % of the context window does this document use? | `token_count / context_window * 100`, rounded to 2 dp | [`context_usage_pct()`](../src/norefund/core/costing.py) |
| Does it fit in one call at all? | `token_count <= context_window` | [`fits_in_context()`](../src/norefund/core/costing.py) |
| How many API calls (chunks) would it take? | `ceil(token_count / (context_window - 1024))` | [`min_chunks()`](../src/norefund/core/costing.py) |

`min_chunks` reserves 1,024 tokens of the window for the model's own output on each
call — a chunked call still needs to *generate* a response, not just consume the whole
window as input. `context_usage_pct` returns `None` (not `0`) when the context window is
zero or unknown, so the UI can show "—" instead of a misleading 0%.

## Cost: tiered pricing

Most providers now price a token differently depending on how big the *prompt* is —
OpenAI, Google, and DeepSeek all have a "long context" tier that kicks in past some
prompt-token threshold, at a higher per-million rate. The tier is always decided by the
**input** size, even when you're pricing the **output** tokens of that same call —
a long prompt makes the completion pricier too, because the model is still attending
over that long context while generating.

```
long_context_active = prompt_tokens > model.long_context_threshold   # if the model has one

input_cost  = (input_tokens  / 1,000,000) * (long_context_input_rate  if active else input_rate)
output_cost = (output_tokens / 1,000,000) * (long_context_output_rate if active else output_rate)
total_cost  = input_cost + output_cost
```

A model with no `long_context_threshold` just always uses its flat rate — the tiered
branch never activates. See
[`_long_context_active()`, `input_cost()`, `output_cost()`, `total_cost()`](../src/norefund/core/costing.py).

**Portfolio projection** (Compare view) extends this same per-call math across a volume
of calls per month — `run_frequency × calls_per_run × total_cost` — see
[`core/portfolio.py`](../src/norefund/core/portfolio.py). No new pricing math, just
multiplication across a schedule.

## Self-host fit: does this model fit on my hardware?

This is the most involved calculation in the app —
[`core/selfhost.py`](../src/norefund/core/selfhost.py) — because "does it fit" depends
on five independent things: model size, quantization, context length, KV-cache
precision, and concurrency.

### 1. Weight memory

```
weight_bytes = round(total_params * bits_per_weight(quantization) / 8)
```

Uses `total_params`, not `active_params` — for a mixture-of-experts model, every expert
must be resident in memory even though only a subset activates per token. `bits_per_weight`
isn't a clean power of two for GGUF K-quants (e.g. Q4_K_M averages 4.8944 bits/weight,
not a naive 4.0) — see [`core/quantization.py`](../src/norefund/core/quantization.py)
for the full table, sourced from llama.cpp's own measured numbers.

### 2. KV-cache memory

The cache that holds attention keys/values for every token already generated, per
sequence. Two attention layouts are supported:

| Attention type | Bytes per layer per token |
|---|---|
| GQA (grouped-query attention) | `2 * n_kv_heads * head_dim * bytes_per_element` |
| MLA (multi-head latent attention, e.g. DeepSeek) | `(kv_lora_rank + qk_rope_head_dim) * bytes_per_element` |

For a normal (full-attention) model, total KV-cache bytes for one sequence at a given
context length is just `bytes_per_layer_per_token * n_layers * context_length`.

**Sliding-window is the one non-linear case.** Gemma 2 alternates one full-attention
layer with one sliding-window layer (`sliding_window_pattern = 2`) — a windowed layer
only ever caches the *last* `sliding_window` tokens, not the whole context, so its cost
stops growing once `context_length` passes the window size:

```
full_layers     = n_layers // sliding_window_pattern
windowed_layers = n_layers - full_layers
windowed_context = min(context_length, sliding_window)

kv_cache_bytes = bytes_per_layer_per_token * (
    full_layers * context_length + windowed_layers * windowed_context
)
```

For every other architecture today, `sliding_window == 0`, so this collapses back to the
plain linear formula. See
[`kv_cache_bytes()`](../src/norefund/core/selfhost.py) and
[`_kv_cache_bytes_per_layer_per_token()`](../src/norefund/core/selfhost.py).

**KV-cache dtype** (separate from weight quantization — serving engines like vLLM and
llama.cpp let you pick these independently) uses its own bytes-per-element table: FP16 =
2 bytes, FP8 = 1 byte, Q8_0 = 1.0625 bytes, Q4_0 = 0.5625 bytes. See
[`bytes_per_kv_element()`](../src/norefund/core/quantization.py).

### 3. Activation memory

The working-set memory needed mid-forward-pass, independent of KV cache:

```
activation_tokens = min(2048, context_length)   # chunked-prefill cap, vLLM's default
activation_bytes = activation_tokens * hidden_size * 16 * 2
```

The 2,048-token cap matters because chunked prefill means this term does **not** grow
with context length beyond that cap — only the KV cache keeps growing. See
[`activation_bytes()`](../src/norefund/core/selfhost.py).

### 4. Framework overhead

A fixed per-device memory tax just to run the serving process itself:
1 GiB per discrete GPU (CUDA context + allocator + NCCL buffers), or 512 MiB per Apple
Silicon device (the lighter Metal/llama.cpp runtime needs less). See
[`framework_overhead_bytes()`](../src/norefund/core/selfhost.py).

### 5. Putting it together

```
total_bytes = weight_bytes + (kv_cache_bytes_per_sequence * concurrency)
            + activation_bytes + framework_overhead_bytes

usable_bytes = total_device_memory * hardware.usable_memory_fraction

fits              = total_bytes <= usable_bytes
headroom_bytes    = usable_bytes - total_bytes          # negative = over budget
utilization_pct   = total_bytes / usable_bytes * 100
max_concurrent     = (usable_bytes - weight_bytes - activation_bytes - overhead)
                      // kv_cache_bytes_per_sequence
```

`usable_memory_fraction` exists because you never get 100% of a device's advertised
memory in practice (driver reservations, OS overhead) — each hardware target in
[`config/hardware.yaml`](../src/norefund/config/hardware.yaml) carries its own measured
fraction. `max_concurrent_requests` answers a different question than `fits` — it's "how
many of *this exact* request could run side by side," independent of the concurrency you
actually asked for. See
[`estimate_memory()`, `max_concurrent_requests()`, `evaluate_fit()`](../src/norefund/core/selfhost.py) —
`evaluate_fit()` is the single entry point that runs all of the above and never raises,
returning a structured `FitResult` with warnings instead (e.g. "this is an MoE model, all
experts must be resident" or "unified memory is shared with the rest of macOS").

## Currency conversion

Every price in the registry is USD. Converting to a display currency is one
multiplication against a cached exchange rate:

```
converted_amount = amount_usd * rates[to_currency]
```

Rates are fetched from `api.frankfurter.dev` (free, ECB-sourced, no API key) only when
you press "Refresh rates" in Settings — never automatically, matching the app's
"network only on explicit action" rule. An unknown currency (e.g. a stale cache missing
one added later) falls through unconverted (rate `1.0`) rather than crashing the UI. See
[`core/currency.py`](../src/norefund/core/currency.py).
