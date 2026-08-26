"""Tests for the model architecture registry."""

import pytest

from norefund.core.architectures import (
    ModelArchitecture,
    find_architecture,
    get_architecture,
    list_architectures,
    load_architectures,
)


def test_load_architectures_returns_dict_of_model_architecture():
    architectures = load_architectures()
    assert len(architectures) > 0
    assert all(isinstance(a, ModelArchitecture) for a in architectures.values())


def test_exactly_fourteen_entries():
    # 13 rows in PLAN.md's table (Llama 3.1 70B and 3.3 70B are separate
    # entries with identical numbers, despite the "~12 models" decision),
    # plus meta:llama-3-8b (Phase 14: every self-hosted model in
    # default_models.yaml must have an architecture entry).
    assert len(list_architectures()) == 14


def test_all_ids_unique():
    ids = [a.id for a in list_architectures()]
    assert len(ids) == len(set(ids))


def test_deepseek_v3_is_mla():
    arch = get_architecture("deepseek:deepseek-v3")
    assert arch.attention_type == "mla"
    assert arch.kv_lora_rank == 512
    assert arch.qk_rope_head_dim == 64
    assert arch.n_layers == 61


def test_llama_70b_gqa_head_counts():
    arch = get_architecture("meta:llama-3.1-70b")
    assert arch.n_kv_heads == 8
    assert arch.n_attention_heads == 64


def test_gemma_2_9b_head_dim_is_not_derivable_from_hidden_size():
    # hidden_size / n_attention_heads = 3584 / 16 = 224, but the real
    # head_dim (copied from config.json) is 256 -- this guards against a
    # future refactor that "simplifies" head_dim into a derived value.
    arch = get_architecture("google:gemma-2-9b")
    assert arch.head_dim == 256
    assert arch.head_dim != arch.hidden_size // arch.n_attention_heads


def test_mixtral_is_moe_active_params_less_than_total():
    arch = get_architecture("mistral:mixtral-8x7b")
    assert arch.active_params < arch.total_params


def test_non_moe_entries_have_equal_active_and_total_params():
    for arch in list_architectures():
        if arch.id == "mistral:mixtral-8x7b" or arch.id == "deepseek:deepseek-v3":
            continue
        assert arch.active_params == arch.total_params


def test_every_entry_kv_heads_not_more_than_attention_heads():
    for arch in list_architectures():
        assert arch.n_kv_heads <= arch.n_attention_heads


def test_all_five_families_present():
    families = {a.family for a in list_architectures()}
    assert families == {"Llama 3", "Qwen 2.5", "Mistral", "Gemma 2", "DeepSeek"}


def test_find_architecture_missing_returns_none():
    assert find_architecture("nope:not-a-model") is None


def test_get_architecture_missing_raises():
    with pytest.raises(ValueError):
        get_architecture("nope:not-a-model")
