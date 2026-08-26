# Data Sources

NoRefund's numbers are only as good as the registry data behind them. This page covers
where that data comes from, what's approximate vs. exact, and the discipline used to
keep it from silently going stale. For the *formulas* that consume this data, see
[Mathematics](MATHEMATICS.md). For a field-by-field guide to actually adding or fixing
an entry, see [Adding a Model](ADDING_A_MODEL.md).

## The three registry files

| File | Contains |
|---|---|
| [`config/default_models.yaml`](../src/norefund/config/default_models.yaml) | Every supported model: context window, pricing, provider, tokenizer, `pricing_verified_on` |
| [`config/model_architectures.yaml`](../src/norefund/config/model_architectures.yaml) | Open-weight model internals needed for self-host math: layer counts, head dimensions, attention type, MLA/GQA parameters |
| [`config/hardware.yaml`](../src/norefund/config/hardware.yaml) | Self-host hardware targets: GPUs, Apple Silicon, cloud instances, with usable-memory fractions |

`tests/test_registry_data.py` enforces cross-file consistency — every architecture id
has a matching registry entry, the two files agree on shared fields, every priced entry
carries a verification date — but a passing test only proves the files agree with each
other. It cannot tell you whether a given price is still *correct*; only re-reading the
provider's page can.

## Where pricing comes from

Prices are read from each provider's own pricing page on the day the registry entry is
edited — never carried forward from memory or from an older PR/plan document (a plan
document's own figures can themselves have drifted by the time anyone acts on them —
this happened once, during a registry refresh, when a reference doc's pricing, recorded
four days earlier, was already wrong by the time it was used).

| Provider | Pricing page |
|---|---|
| OpenAI | https://developers.openai.com/api/docs/pricing |
| Anthropic | https://platform.claude.com/docs/en/about-claude/pricing |
| Google | https://ai.google.dev/gemini-api/docs/pricing |
| DeepSeek | https://api-docs.deepseek.com/quick_start/pricing |

`pricing_verified_on` on a `ModelInfo` entry moves **only** when a human (or an agent
acting on a human's behalf) has actually opened that page on that date and read the
number off it — never bumped just to "look current."

## Where architecture data comes from

Layer counts, head dimensions, MLA parameters, and context windows come from the
model's published HuggingFace `config.json`. Parameter counts are cross-checked against
the HF API's safetensors total (`GET /api/models/{repo}?blobs=true`, the
`safetensors.total` field) rather than trusted from a model card's rounded number.

### Verifying licence-gated mirrors

Some models (see the `meta:llama-*` and `google:gemma-2-*` entries) are gated on
HuggingFace, requiring an ungated substitute repo to point the tokenizer at instead.
Trusting a mirror's *name* isn't enough — identity is verified via the HF tree API's git
blob oid for the specific file in question:

```
GET /api/models/{repo}/tree/main
```

An identical oid between the official gated repo and the ungated mirror proves the file
is byte-identical, without needing to authenticate to the gated repo or download either
copy.

## Tokenizer accuracy

NoRefund runs the real tokenizer for OpenAI, DeepSeek V3, Llama, Qwen, and Mistral
models. Anthropic and Google don't publish a downloadable tokenizer for Claude or
Gemini, so those four entries fall back to a `cl100k_base` approximation:

| Model | `tokenizer_is_approximate` |
|---|---|
| `anthropic:claude-sonnet-5` | `true` |
| `anthropic:claude-haiku-4.5` | `true` |
| `google:gemini-3.5-flash` | `true` |
| `google:gemini-3.1-pro-preview` | `true` |

Every other registry entry has this field unset (`false`). The app marks approximate
counts `(approx.)` everywhere they're shown, so an approximation is never presented as
an exact count.

## Tokenizer downloads

Tokenizer vocab files aren't bundled with the app — the first time you use a given
tokenizer, NoRefund needs to fetch its vocab files once (this is one of the two places
in the whole codebase that touches the network; see
[`resources.download_tokenizer()`](../src/norefund/core/resources/download.py)). The
in-app **Resources** view shows what's cached, where it lives on disk, and how much
space it uses, with a one-click download for anything missing. Once cached, NoRefund
never touches the network again for that tokenizer — if it isn't cached yet, the app
raises a clear error pointing you to the Resources view instead of silently downloading
it mid-analysis.

## Refreshing the registry

When re-verifying or updating registry data:

1. Re-read the provider's pricing page (table above) — don't trust a cached memory of
   the number.
2. Re-read the model's HuggingFace `config.json` for architecture fields; cross-check
   the parameter count against the safetensors API.
3. For gated models, verify the mirror's git blob oid before pointing the tokenizer at
   it (see above).
4. Update `pricing_verified_on` to the date you actually did this.
5. Run `pytest tests/test_registry_data.py` to confirm the two registry files still
   agree with each other.
