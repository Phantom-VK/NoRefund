"""Quantization constant tables: bits-per-weight and KV-cache bytes-per-element.

These are format constants defined by the GGUF/GPTQ/AWQ block layouts and by
IEEE float sizes -- not user data -- so they live in code, not YAML.

GGUF K-quants are not clean powers of two: the "_M" variants mix in a higher
k-quant for a few tensors and keep embeddings at higher precision, so the
real average is e.g. 4.8944 bits/weight for Q4_K_M, not a naive 4.0. Values
below are llama.cpp's own measured numbers for Llama-3.1-8B (see PLAN.md
Phase 1 for the full derivation and sources).
"""

from __future__ import annotations

# Bits per weight, after quantization. Order here is display order.
_BITS_PER_WEIGHT: dict[str, float] = {
    "fp32": 32.0,
    "fp16": 16.0,
    "bf16": 16.0,
    "fp8": 8.0,
    "int8": 8.0,
    "q8_0": 8.5008,
    "q6_k": 6.5633,
    "q5_k_m": 5.7036,
    "q4_k_m": 4.8944,
    "int4": 4.15,
}

# Bytes per KV-cache element. Independent of weight quantization -- serving
# engines (vLLM, llama.cpp) let you pick these separately.
_BYTES_PER_KV_ELEMENT: dict[str, float] = {
    "fp16": 2.0,
    "fp8": 1.0,
    "q8_0": 1.0625,
    "q4_0": 0.5625,
}

_DISPLAY_NAMES: dict[str, str] = {
    "fp32": "FP32",
    "fp16": "FP16",
    "bf16": "BF16",
    "fp8": "FP8",
    "int8": "INT8",
    "q8_0": "Q8_0",
    "q6_k": "Q6_K",
    "q5_k_m": "Q5_K_M",
    "q4_k_m": "Q4_K_M",
    "int4": "INT4",
    "q4_0": "Q4_0",
}


def bits_per_weight(level: str) -> float | None:
    """Bits per weight for a quantization level, or None if unknown."""
    return _BITS_PER_WEIGHT.get(level)


def bytes_per_kv_element(dtype: str) -> float | None:
    """Bytes per KV-cache element for a KV cache dtype, or None if unknown."""
    return _BYTES_PER_KV_ELEMENT.get(dtype)


def quantization_display_name(level: str) -> str | None:
    """Human-readable label with bpw, e.g. 'Q4_K_M (4.89 bpw)'."""
    bpw = _BITS_PER_WEIGHT.get(level)
    if bpw is None:
        return None
    return f"{_DISPLAY_NAMES[level]} ({bpw:.2f} bpw)"


def kv_cache_dtype_display_name(dtype: str) -> str | None:
    """Human-readable label with byte size, e.g. 'FP8 (1 byte)'."""
    bytes_per_element = _BYTES_PER_KV_ELEMENT.get(dtype)
    if bytes_per_element is None:
        return None
    return f"{_DISPLAY_NAMES[dtype]} ({bytes_per_element:g} bytes)"


def list_quantization_levels() -> list[str]:
    """All supported quantization level keys, fp32 first."""
    return list(_BITS_PER_WEIGHT.keys())


def list_kv_cache_dtypes() -> list[str]:
    """All supported KV-cache dtype keys, fp16 first."""
    return list(_BYTES_PER_KV_ELEMENT.keys())
