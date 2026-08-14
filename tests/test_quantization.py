"""Tests for quantization constant tables."""

from norefund.core.quantization import (
    bits_per_weight,
    bytes_per_kv_element,
    kv_cache_dtype_display_name,
    list_kv_cache_dtypes,
    list_quantization_levels,
    quantization_display_name,
)


def test_bits_per_weight_fp16():
    assert bits_per_weight("fp16") == 16.0


def test_bits_per_weight_q4_k_m():
    # llama.cpp's own measured value for Llama-3.1-8B, not a naive 4.0 --
    # the "_M" k-quant mix runs above the base Q4_K's 4.5 bpw.
    assert bits_per_weight("q4_k_m") == 4.8944


def test_bits_per_weight_q8_0_and_int8_are_different_formats():
    # q8_0 (GGUF block-32, includes a per-block fp16 scale) and int8
    # (plain W8A8) are both "8-bit" but not the same format or size.
    assert bits_per_weight("q8_0") == 8.5008
    assert bits_per_weight("int8") == 8.0


def test_bits_per_weight_q6_k():
    assert bits_per_weight("q6_k") == 6.5633


def test_bits_per_weight_unknown_returns_none():
    assert bits_per_weight("nope") is None


def test_bytes_per_kv_element_fp8():
    assert bytes_per_kv_element("fp8") == 1.0


def test_bytes_per_kv_element_q4_0():
    assert bytes_per_kv_element("q4_0") == 0.5625


def test_bytes_per_kv_element_unknown_returns_none():
    assert bytes_per_kv_element("nope") is None


def test_list_quantization_levels_has_all_ten_fp32_first():
    levels = list_quantization_levels()
    assert len(levels) == 10
    assert levels[0] == "fp32"
    assert "q4_k_m" in levels


def test_list_kv_cache_dtypes_has_all_four():
    assert set(list_kv_cache_dtypes()) == {"fp16", "fp8", "q8_0", "q4_0"}


def test_quantization_display_name():
    assert quantization_display_name("q4_k_m") == "Q4_K_M (4.89 bpw)"


def test_quantization_display_name_unknown_returns_none():
    assert quantization_display_name("nope") is None


def test_kv_cache_dtype_display_name():
    assert kv_cache_dtype_display_name("fp8") == "FP8 (1 bytes)"
