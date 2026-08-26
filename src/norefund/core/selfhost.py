"""Pure VRAM-fit math for self-hosting an open-weight model.

No I/O here -- mirrors costing.py. Everything is plain functions over
ModelArchitecture / HardwareTarget values; nothing here calls a YAML loader.
See PLAN.md Phase 1 (or docs/PLAN_WALKTHROUGH.md for a plain-language
explanation) for the derivation of every formula and constant below.
"""

from __future__ import annotations

from dataclasses import dataclass

from norefund.core.architectures import ModelArchitecture
from norefund.core.hardware_registry import HardwareTarget
from norefund.core.quantization import bits_per_weight, bytes_per_kv_element

_GIB = 1024**3

# Fixed per-device memory tax just to run the serving process itself
# (CUDA context + allocator + NCCL buffers vs. the lighter Metal/llama.cpp
# runtime on Apple Silicon).
_FRAMEWORK_OVERHEAD_DISCRETE = 1 * _GIB
_FRAMEWORK_OVERHEAD_UNIFIED = 512 * 1024 * 1024

# Activation working-set sizing: chunked prefill caps the per-forward-pass
# token budget (vLLM's max_num_batched_tokens default), so this term does
# not grow with concurrency -- only the KV cache does.
_PREFILL_CHUNK_TOKENS = 2_048
_ACTIVATION_ELEMENTS_PER_TOKEN_PER_HIDDEN = 16
_ACTIVATION_BYTES_PER_ELEMENT = 2


@dataclass(frozen=True)
class MemoryEstimate:
    weights_bytes: int
    kv_cache_bytes_per_sequence: int
    kv_cache_bytes: int
    activation_bytes: int
    framework_overhead_bytes: int
    total_bytes: int


@dataclass(frozen=True)
class FitResult:
    architecture_id: str
    hardware_id: str
    quantization: str
    kv_cache_dtype: str
    context_length: int
    concurrency: int  # the effective (clamped to >= 0) value
    usable_memory_bytes: int
    estimate: MemoryEstimate | None
    fits: bool
    headroom_bytes: int | None  # signed: negative means over budget
    utilization_pct: float | None
    max_concurrent_requests: int | None
    warnings: tuple[str, ...] = ()
    error: str | None = None


def total_memory_bytes(hardware: HardwareTarget) -> int:
    device_count = max(hardware.device_count, 1)
    return round(hardware.memory_gib_per_device * _GIB) * device_count


def usable_memory_bytes(hardware: HardwareTarget) -> int:
    fraction = min(max(hardware.usable_memory_fraction, 0.0), 1.0)
    return max(0, round(total_memory_bytes(hardware) * fraction))


def framework_overhead_bytes(hardware: HardwareTarget) -> int:
    per_device = (
        _FRAMEWORK_OVERHEAD_UNIFIED
        if hardware.memory_kind == "unified"
        else _FRAMEWORK_OVERHEAD_DISCRETE
    )
    return per_device * max(hardware.device_count, 1)


def weight_bytes(architecture: ModelArchitecture, quantization: str) -> int | None:
    """Model weight memory. Uses total_params (not active_params) for MoE
    models, since every expert must be resident even though only a subset
    activates per token."""
    bpw = bits_per_weight(quantization)
    if bpw is None or architecture.total_params <= 0:
        return None
    return round(architecture.total_params * bpw / 8)


def _kv_cache_bytes_per_layer_per_token(
    architecture: ModelArchitecture, kv_cache_dtype: str
) -> float | None:
    """Unrounded KV-cache bytes for one layer, one token, one sequence.

    Shared by kv_cache_bytes_per_token and kv_cache_bytes so both round
    only once, at the end, rather than compounding rounding error by
    dividing an already-rounded per-token total by n_layers.
    """
    bytes_per_element = bytes_per_kv_element(kv_cache_dtype)
    if bytes_per_element is None:
        return None
    if architecture.attention_type == "gqa":
        return 2 * architecture.n_kv_heads * architecture.head_dim * bytes_per_element
    if architecture.attention_type == "mla":
        if architecture.kv_lora_rank <= 0:
            return None
        return (
            architecture.kv_lora_rank + architecture.qk_rope_head_dim
        ) * bytes_per_element
    return None


def kv_cache_bytes_per_token(
    architecture: ModelArchitecture, kv_cache_dtype: str = "fp16"
) -> int | None:
    """KV-cache memory for one token, one sequence, as if every layer were
    full attention. Ignores sliding-window; see kv_cache_bytes for
    context-length-aware sizing that accounts for it."""
    per_layer = _kv_cache_bytes_per_layer_per_token(architecture, kv_cache_dtype)
    if per_layer is None:
        return None
    return round(architecture.n_layers * per_layer)


def kv_cache_bytes(
    architecture: ModelArchitecture, context_length: int, kv_cache_dtype: str = "fp16"
) -> int | None:
    """KV-cache memory for one sequence at context_length.

    Sliding-window KV cost is not linear in context length the way full
    attention's is: a windowed layer caches only min(context_length,
    sliding_window) tokens, while a full-attention layer caches the whole
    context_length. architecture.sliding_window == 0 (every architecture
    except Gemma 2 today) means every layer is full attention, which
    reduces this to kv_cache_bytes_per_token(...) * context_length.
    """
    per_layer = _kv_cache_bytes_per_layer_per_token(architecture, kv_cache_dtype)
    if per_layer is None or architecture.n_layers <= 0:
        return None
    if architecture.sliding_window <= 0 or architecture.sliding_window_pattern <= 0:
        return round(architecture.n_layers * per_layer * context_length)

    full_layers = architecture.n_layers // architecture.sliding_window_pattern
    windowed_layers = architecture.n_layers - full_layers
    windowed_context = min(context_length, architecture.sliding_window)
    return round(
        per_layer * (full_layers * context_length + windowed_layers * windowed_context)
    )


def activation_bytes(architecture: ModelArchitecture, context_length: int) -> int:
    if context_length <= 0:
        return 0
    activation_tokens = min(_PREFILL_CHUNK_TOKENS, context_length)
    return (
        activation_tokens
        * architecture.hidden_size
        * _ACTIVATION_ELEMENTS_PER_TOKEN_PER_HIDDEN
        * _ACTIVATION_BYTES_PER_ELEMENT
    )


def estimate_memory(
    architecture: ModelArchitecture,
    hardware: HardwareTarget,
    quantization: str,
    context_length: int,
    *,
    concurrency: int = 1,
    kv_cache_dtype: str = "fp16",
) -> MemoryEstimate | None:
    weights = weight_bytes(architecture, quantization)
    kv_per_sequence = kv_cache_bytes(architecture, context_length, kv_cache_dtype)
    if weights is None or kv_per_sequence is None or context_length <= 0:
        return None

    kv_total = kv_per_sequence * max(concurrency, 0)
    activation = activation_bytes(architecture, context_length)
    overhead = framework_overhead_bytes(hardware)

    return MemoryEstimate(
        weights_bytes=weights,
        kv_cache_bytes_per_sequence=kv_per_sequence,
        kv_cache_bytes=kv_total,
        activation_bytes=activation,
        framework_overhead_bytes=overhead,
        total_bytes=weights + kv_total + activation + overhead,
    )


def max_concurrent_requests(
    architecture: ModelArchitecture,
    hardware: HardwareTarget,
    quantization: str,
    context_length: int,
    *,
    kv_cache_dtype: str = "fp16",
) -> int | None:
    """How many concurrent full-context sequences could fit, independent of
    the requested concurrency."""
    weights = weight_bytes(architecture, quantization)
    kv_per_sequence = kv_cache_bytes(architecture, context_length, kv_cache_dtype)
    if weights is None or kv_per_sequence is None or context_length <= 0:
        return None

    activation = activation_bytes(architecture, context_length)
    overhead = framework_overhead_bytes(hardware)
    available_for_kv = usable_memory_bytes(hardware) - weights - activation - overhead
    if available_for_kv <= 0:
        return 0

    if kv_per_sequence <= 0:
        return None
    return available_for_kv // kv_per_sequence


def evaluate_fit(
    architecture: ModelArchitecture | None,
    hardware: HardwareTarget | None,
    quantization: str,
    context_length: int,
    *,
    concurrency: int = 1,
    kv_cache_dtype: str = "fp16",
) -> FitResult:
    """The single entry point: does this model fit on this hardware, and
    how many concurrent requests can it serve? Never raises."""
    effective_concurrency = max(concurrency, 0)

    def _error(message: str, usable: int = 0) -> FitResult:
        return FitResult(
            architecture_id=architecture.id if architecture is not None else "",
            hardware_id=hardware.id if hardware is not None else "",
            quantization=quantization,
            kv_cache_dtype=kv_cache_dtype,
            context_length=context_length,
            concurrency=effective_concurrency,
            usable_memory_bytes=usable,
            estimate=None,
            fits=False,
            headroom_bytes=None,
            utilization_pct=None,
            max_concurrent_requests=None,
            warnings=(),
            error=message,
        )

    if architecture is None:
        return _error("No architecture data available for this model.")
    if hardware is None:
        return _error("No hardware target selected.")

    usable = usable_memory_bytes(hardware)

    if bits_per_weight(quantization) is None:
        return _error(f"Unknown quantization level '{quantization}'.", usable)
    if bytes_per_kv_element(kv_cache_dtype) is None:
        return _error(f"Unknown KV cache dtype '{kv_cache_dtype}'.", usable)
    if context_length <= 0:
        return _error("Context length must be greater than zero.", usable)
    if architecture.total_params <= 0:
        return _error("Model architecture has no parameter count.", usable)
    if architecture.attention_type == "mla" and architecture.kv_lora_rank <= 0:
        return _error("Architecture is marked MLA but has no kv_lora_rank.", usable)
    if architecture.attention_type not in ("gqa", "mla"):
        return _error(
            f"Unknown attention type '{architecture.attention_type}'.", usable
        )

    estimate = estimate_memory(
        architecture,
        hardware,
        quantization,
        context_length,
        concurrency=effective_concurrency,
        kv_cache_dtype=kv_cache_dtype,
    )
    assert estimate is not None  # all preconditions above already checked

    fits = estimate.total_bytes <= usable
    headroom = usable - estimate.total_bytes
    utilization = round(estimate.total_bytes / usable * 100, 2) if usable > 0 else None
    max_concurrent = max_concurrent_requests(
        architecture,
        hardware,
        quantization,
        context_length,
        kv_cache_dtype=kv_cache_dtype,
    )

    warnings: list[str] = []
    if context_length > architecture.max_context_length:
        warnings.append(
            f"Requested context of {context_length:,} tokens exceeds "
            f"{architecture.display_name}'s "
            f"{architecture.max_context_length:,}-token maximum."
        )
    if architecture.active_params != architecture.total_params:
        warnings.append(
            f"{architecture.display_name} is a mixture-of-experts model: all "
            f"{architecture.total_params:,} parameters must be resident in "
            f"memory even though only {architecture.active_params:,} are "
            "active per token."
        )
    if (
        architecture.attention_type == "gqa"
        and hardware.device_count > 1
        and architecture.n_kv_heads % hardware.device_count != 0
    ):
        warnings.append(
            f"Tensor parallelism across {hardware.device_count} devices "
            f"requires the KV head count ({architecture.n_kv_heads}) to be "
            f"divisible by {hardware.device_count}."
        )
    if hardware.memory_kind == "unified":
        warnings.append(
            "Unified memory is shared with macOS and other running "
            "applications — close other apps before loading."
        )

    return FitResult(
        architecture_id=architecture.id,
        hardware_id=hardware.id,
        quantization=quantization,
        kv_cache_dtype=kv_cache_dtype,
        context_length=context_length,
        concurrency=effective_concurrency,
        usable_memory_bytes=usable,
        estimate=estimate,
        fits=fits,
        headroom_bytes=headroom,
        utilization_pct=utilization,
        max_concurrent_requests=max_concurrent,
        warnings=tuple(warnings),
        error=None,
    )
