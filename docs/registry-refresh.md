# Refreshing the model registry

`src/norefund/config/default_models.yaml` and `model_architectures.yaml` are
read against primary sources, not updated from memory or from a previous
model's own claims about itself. Pricing comes from each provider's own
pricing page, re-read on the day the file is edited: OpenAI
(`https://developers.openai.com/api/docs/pricing`), Anthropic
(`https://platform.claude.com/docs/en/about-claude/pricing`), Google
(`https://ai.google.dev/gemini-api/docs/pricing`), and DeepSeek
(`https://api-docs.deepseek.com/quick_start/pricing`). Architecture fields
(layer counts, head dimensions, MLA parameters, context windows) come from
the model's published HuggingFace `config.json`, and parameter counts are
cross-checked against the HF API's safetensors total
(`GET /api/models/{repo}?blobs=true`, the `safetensors.total` field) rather
than trusted from a model card's rounded number.

`pricing_verified_on` on a `ModelInfo` entry moves only when a human (or an
agent acting on a human's behalf) has actually opened the provider's page
that day and read the number off it -- never bumped to "look current"
without doing that, and never copied forward from an older PR or plan
document, which can itself have drifted by the time anyone acts on it (this
happened during the Phase 14 registry refresh: a reference doc's own
pricing figures, recorded four days earlier, were already wrong by the time
they were used). `tests/test_registry_data.py` enforces the structural
invariants this depends on -- every architecture id has a matching registry
entry, the two files agree on shared fields, every priced entry carries a
verification date -- but it cannot check whether a given date's price is
still correct; only re-reading the source page can.

When a licence-gated HuggingFace repo needs an ungated substitute (see the
comments on the `meta:llama-*` and `google:gemma-2-*` entries), verify
identity via the HF tree API's git blob oid for the file in question
(`GET /api/models/{repo}/tree/main`) rather than trusting a mirror's name --
an identical oid between the official repo and the mirror proves the file
is byte-identical without needing to authenticate to the gated repo or
download either copy.
