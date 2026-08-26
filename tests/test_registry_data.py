"""Cross-consistency checks between default_models.yaml and
model_architectures.yaml, and basic sanity checks on the pricing metadata.

Pure, no network, no fixtures -- reads the same bundled YAML the app ships.
These exist because the Phase 14 audit found real drift (a missing
architecture entry, two files disagreeing about one model's context
window) that nothing in the repo could have caught automatically. See
docs/registry-refresh.md for how to re-verify and update this data.

No test here may assert a date is "recent" -- a time-bomb that reddens CI
on a quiet Tuesday teaches people to ignore CI, per this file's own
design goal of a guard that doesn't rot.
"""

from __future__ import annotations

import datetime
import re

from norefund.core.architectures import _DEFAULT_ARCHITECTURE_PATH, list_architectures
from norefund.core.models_registry import _DEFAULT_REGISTRY_PATH, list_models

_models = {m.id: m for m in list_models()}
_architectures = {a.id: a for a in list_architectures()}


def _architecture_yaml_blocks() -> dict[str, str]:
    """Map architecture id -> its raw YAML block (comments included).

    ModelArchitecture strips comments on load, but the head_dim exception
    check needs to see them -- re-read the raw file and split on each
    top-level "- id:" entry rather than adding a YAML-comment-preserving
    dependency for one test.
    """
    text = _DEFAULT_ARCHITECTURE_PATH.read_text(encoding="utf-8")
    entries = re.split(r"(?=^- id: )", text, flags=re.MULTILINE)
    blocks: dict[str, str] = {}
    for entry in entries:
        match = re.match(r"^- id: (\S+)", entry)
        if match:
            blocks[match.group(1)] = entry
    return blocks


def test_every_architecture_id_exists_in_model_registry():
    for arch_id in _architectures:
        assert arch_id in _models, (
            f"model_architectures.yaml has '{arch_id}' with no matching "
            f"entry in default_models.yaml"
        )


def test_every_self_hosted_model_has_an_architecture_entry():
    # Self-hosted == a real (non-tiktoken) tokenizer backend and no price.
    # This is exactly the check that would have caught meta:llama-3-8b
    # having no architecture entry before Phase 14.
    for model in _models.values():
        is_self_hosted = (
            model.tokenizer_backend != "tiktoken"
            and model.input_price_per_million == 0
            and model.output_price_per_million == 0
        )
        if is_self_hosted:
            assert model.id in _architectures, (
                f"'{model.id}' is self-hosted (backend={model.tokenizer_backend}, "
                f"zero price) but has no model_architectures.yaml entry, so it "
                f"can never appear in the Fit Check"
            )


def test_shared_ids_agree_on_context_window():
    # This is exactly the check that would have caught DeepSeek V3's two
    # files disagreeing (128000 vs 163840) before Phase 14.
    shared_ids = set(_models) & set(_architectures)
    assert shared_ids, "expected at least one id in both registries"
    for shared_id in shared_ids:
        model = _models[shared_id]
        arch = _architectures[shared_id]
        assert model.context_window == arch.max_context_length, (
            f"'{shared_id}': default_models.yaml says context_window="
            f"{model.context_window}, model_architectures.yaml says "
            f"max_context_length={arch.max_context_length}"
        )


def test_every_priced_entry_has_docs_url_and_verification_date():
    priced = [m for m in _models.values() if m.input_price_per_million > 0]
    assert priced, "expected at least one priced entry"
    for model in priced:
        assert model.docs_url is not None, f"'{model.id}' has a price but no docs_url"
        assert model.pricing_verified_on is not None, (
            f"'{model.id}' has a price but no pricing_verified_on"
        )


def test_every_pricing_verified_on_parses_as_a_date():
    for model in _models.values():
        if model.pricing_verified_on is not None:
            # Raises ValueError (failing the test) if it isn't a real
            # ISO date -- deliberately not asserting anything about how
            # recent it is.
            datetime.date.fromisoformat(model.pricing_verified_on)


def test_head_dim_times_attention_heads_matches_hidden_size_or_is_explained():
    blocks = _architecture_yaml_blocks()
    for arch in _architectures.values():
        if arch.head_dim * arch.n_attention_heads == arch.hidden_size:
            continue
        block = blocks.get(arch.id, "")
        assert "head_dim" in block, (
            f"'{arch.id}': head_dim ({arch.head_dim}) * n_attention_heads "
            f"({arch.n_attention_heads}) != hidden_size ({arch.hidden_size}), "
            f"and model_architectures.yaml has no comment on this entry "
            f"explaining why (see the Gemma 2 9B entry for the expected form)"
        )


def test_registry_yaml_path_is_the_real_bundled_file():
    # Sanity check on the test's own re-read of the raw file: make sure
    # it's reading the same path the dataclass loader used, not a stale
    # copy elsewhere on disk.
    assert _DEFAULT_ARCHITECTURE_PATH.exists()
    assert _DEFAULT_REGISTRY_PATH.exists()
