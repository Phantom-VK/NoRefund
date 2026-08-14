"""Tests for the pure self-host VRAM fit math.

Fixtures are literal ModelArchitecture/HardwareTarget values (not loaded
from YAML) so these tests exercise the math in isolation. Several
assertions are cross-validated against numbers published outside this
codebase (DeepSeek's own hardware paper, llama.cpp's measured GGUF sizes)
rather than only checking internal self-consistency -- see PLAN.md Phase 1
section 1.11 for the sources.
"""

from norefund.core.architectures import ModelArchitecture
from norefund.core.hardware_registry import HardwareTarget
from norefund.core.selfhost import (
    estimate_memory,
    evaluate_fit,
    framework_overhead_bytes,
    kv_cache_bytes_per_token,
    max_concurrent_requests,
    usable_memory_bytes,
    weight_bytes,
)

_LLAMA_8B = ModelArchitecture(
    id="meta:llama-3.1-8b",
    display_name="Llama 3.1 8B",
    family="Llama 3",
    vendor="Meta",
    total_params=8_030_000_000,
    active_params=8_030_000_000,
    n_layers=32,
    n_attention_heads=32,
    n_kv_heads=8,
    head_dim=128,
    hidden_size=4096,
    max_context_length=131072,
    attention_type="gqa",
)

_LLAMA_70B = ModelArchitecture(
    id="meta:llama-3.1-70b",
    display_name="Llama 3.1 70B",
    family="Llama 3",
    vendor="Meta",
    total_params=70_550_000_000,
    active_params=70_550_000_000,
    n_layers=80,
    n_attention_heads=64,
    n_kv_heads=8,
    head_dim=128,
    hidden_size=8192,
    max_context_length=131072,
    attention_type="gqa",
)

_LLAMA_405B = ModelArchitecture(
    id="meta:llama-3.1-405b",
    display_name="Llama 3.1 405B",
    family="Llama 3",
    vendor="Meta",
    total_params=405_850_000_000,
    active_params=405_850_000_000,
    n_layers=126,
    n_attention_heads=128,
    n_kv_heads=8,
    head_dim=128,
    hidden_size=16384,
    max_context_length=131072,
    attention_type="gqa",
)

_QWEN_72B = ModelArchitecture(
    id="qwen:qwen2.5-72b",
    display_name="Qwen2.5 72B",
    family="Qwen 2.5",
    vendor="Qwen",
    total_params=72_710_000_000,
    active_params=72_710_000_000,
    n_layers=80,
    n_attention_heads=64,
    n_kv_heads=8,
    head_dim=128,
    hidden_size=8192,
    max_context_length=131072,
    attention_type="gqa",
)

_MIXTRAL = ModelArchitecture(
    id="mistral:mixtral-8x7b",
    display_name="Mixtral 8x7B",
    family="Mistral",
    vendor="Mistral",
    total_params=46_700_000_000,
    active_params=12_900_000_000,  # MoE: fewer active than total
    n_layers=32,
    n_attention_heads=32,
    n_kv_heads=8,
    head_dim=128,
    hidden_size=4096,
    max_context_length=32768,
    attention_type="gqa",
)

_DEEPSEEK_V3 = ModelArchitecture(
    id="deepseek:deepseek-v3",
    display_name="DeepSeek V3",
    family="DeepSeek",
    vendor="DeepSeek",
    total_params=671_000_000_000,
    active_params=37_000_000_000,
    n_layers=61,
    n_attention_heads=128,
    n_kv_heads=128,
    head_dim=128,
    hidden_size=7168,
    max_context_length=163840,
    attention_type="mla",
    kv_lora_rank=512,
    qk_rope_head_dim=64,
)

_DEEPSEEK_V3_BAD_MLA = ModelArchitecture(
    id="deepseek:bad",
    display_name="DeepSeek Bad",
    family="DeepSeek",
    vendor="DeepSeek",
    total_params=671_000_000_000,
    active_params=37_000_000_000,
    n_layers=61,
    n_attention_heads=128,
    n_kv_heads=128,
    head_dim=128,
    hidden_size=7168,
    max_context_length=163840,
    attention_type="mla",
    kv_lora_rank=0,  # missing MLA data
    qk_rope_head_dim=64,
)

_A100_80 = HardwareTarget(
    id="test:a100-80",
    display_name="Test A100 80GB",
    category="datacenter_gpu",
    vendor="NVIDIA",
    accelerator="A100",
    device_count=1,
    memory_gib_per_device=80.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)

_RTX_4090 = HardwareTarget(
    id="test:rtx-4090",
    display_name="Test RTX 4090 24GB",
    category="consumer",
    vendor="NVIDIA",
    accelerator="RTX 4090",
    device_count=1,
    memory_gib_per_device=24.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)

_H100_X8 = HardwareTarget(
    id="test:h100-x8",
    display_name="Test 8x H100 80GB",
    category="datacenter_gpu",
    vendor="NVIDIA",
    accelerator="8x H100",
    device_count=8,
    memory_gib_per_device=80.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)

_H200_X8 = HardwareTarget(
    id="test:h200-x8",
    display_name="Test 8x H200 141GB",
    category="datacenter_gpu",
    vendor="NVIDIA",
    accelerator="8x H200",
    device_count=8,
    memory_gib_per_device=141.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)

_THREE_DEVICE = HardwareTarget(
    id="test:three-device",
    display_name="Test 3x GPU",
    category="datacenter_gpu",
    vendor="NVIDIA",
    accelerator="3x A100",
    device_count=3,
    memory_gib_per_device=80.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)

_M2_ULTRA = HardwareTarget(
    id="test:m2-ultra",
    display_name="Test M2 Ultra 192GB",
    category="consumer",
    vendor="Apple",
    accelerator="Apple M2 Ultra",
    device_count=1,
    memory_gib_per_device=192.0,
    memory_kind="unified",
    usable_memory_fraction=0.75,
)

_GEMMA_9B = ModelArchitecture(
    id="google:gemma-2-9b",
    display_name="Gemma 2 9B",
    family="Gemma 2",
    vendor="Google",
    total_params=9_240_000_000,
    active_params=9_240_000_000,
    n_layers=42,
    n_attention_heads=16,
    n_kv_heads=8,
    head_dim=256,
    hidden_size=3584,
    max_context_length=8192,
    attention_type="gqa",
)

_ZERO_VRAM = HardwareTarget(
    id="test:zero-vram",
    display_name="Test zero VRAM",
    category="datacenter_gpu",
    vendor="NVIDIA",
    accelerator="broken",
    device_count=1,
    memory_gib_per_device=0.0,
    memory_kind="discrete",
    usable_memory_fraction=0.90,
)


# --- Cross-validation against numbers published outside this codebase ---


def test_deepseek_v3_kv_cache_matches_published_hardware_paper():
    # DeepSeek's own hardware paper (arXiv 2505.09343, Table 1) publishes
    # 70.272 KB/token for DeepSeek V3's MLA KV cache.
    assert kv_cache_bytes_per_token(_DEEPSEEK_V3) == 70_272


def test_qwen_72b_kv_cache_matches_published_hardware_paper():
    # Same table: 327.680 KB/token for Qwen2.5 72B.
    assert kv_cache_bytes_per_token(_QWEN_72B) == 327_680


def test_llama_405b_kv_cache_matches_published_hardware_paper():
    # Same table: 516.096 KB/token for Llama 3.1 405B.
    assert kv_cache_bytes_per_token(_LLAMA_405B) == 516_096


def test_llama_70b_weight_memory_matches_known_q4_figure():
    # The widely cited "Llama 3 70B needs ~40GB at 4-bit" figure.
    gib = weight_bytes(_LLAMA_70B, "q4_k_m") / 2**30
    assert 39.0 <= gib <= 41.0


def test_llama_8b_weight_memory_matches_llamacpp_published_size():
    # llama.cpp publishes 4.58 GiB for Llama-3.1-8B-Instruct.Q4_K_M.gguf.
    gib = weight_bytes(_LLAMA_8B, "q4_k_m") / 2**30
    assert 4.50 <= gib <= 4.65


def test_mixtral_weight_memory_uses_total_not_active_params():
    # Real Mixtral-8x7B-Instruct-v0.1.Q4_K_M.gguf is 26.4 GiB.
    gib = weight_bytes(_MIXTRAL, "q4_k_m") / 2**30
    assert 26.0 <= gib <= 27.5
    # Using active_params (12.9B) instead of total_params (46.7B) would
    # give roughly a third of this -- lock in that we used total_params.
    active_only_bytes = round(_MIXTRAL.active_params * 4.8944 / 8)
    assert weight_bytes(_MIXTRAL, "q4_k_m") > active_only_bytes * 3


def test_llama_70b_kv_cache_uses_kv_heads_not_attention_heads():
    # n_attention_heads=64 vs n_kv_heads=8 -- using 64 would give 2_621_440
    # (exactly 8x this value).
    assert kv_cache_bytes_per_token(_LLAMA_70B) == 327_680


# --- Hand-computed scenarios ---


def test_scenario_a_llama_70b_q4_on_a100_80gb():
    estimate = estimate_memory(
        _LLAMA_70B, _A100_80, "q4_k_m", 8192, concurrency=1, kv_cache_dtype="fp16"
    )
    assert estimate is not None
    assert estimate.kv_cache_bytes_per_sequence == 2_684_354_560  # exactly 2.5 GiB
    assert estimate.activation_bytes == 536_870_912  # exactly 0.5 GiB
    assert estimate.framework_overhead_bytes == 1_073_741_824
    assert usable_memory_bytes(_A100_80) == 77_309_411_328  # 80 GiB * 0.90
    assert round(estimate.weights_bytes / 2**30, 2) == 40.2

    result = evaluate_fit(_LLAMA_70B, _A100_80, "q4_k_m", 8192, concurrency=1)
    assert result.fits is True
    assert result.max_concurrent_requests == 12


def test_scenario_b_llama_8b_fp16_131k_context_on_rtx_4090():
    estimate = estimate_memory(
        _LLAMA_8B, _RTX_4090, "fp16", 131072, concurrency=1, kv_cache_dtype="fp16"
    )
    assert estimate is not None
    assert estimate.kv_cache_bytes_per_sequence == 17_179_869_184  # exactly 16 GiB

    result = evaluate_fit(_LLAMA_8B, _RTX_4090, "fp16", 131072, concurrency=1)
    assert result.fits is False
    assert result.headroom_bytes < 0
    assert result.max_concurrent_requests == 0


# --- KV cache quantization is independent of weight quantization ---


def test_fp8_kv_cache_halves_fp16_kv_cache():
    fp16 = kv_cache_bytes_per_token(_LLAMA_70B, "fp16")
    fp8 = kv_cache_bytes_per_token(_LLAMA_70B, "fp8")
    assert fp8 == fp16 // 2


def test_q4_0_kv_cache_is_smaller_than_fp16():
    fp16 = kv_cache_bytes_per_token(_LLAMA_70B, "fp16")
    q4_0 = kv_cache_bytes_per_token(_LLAMA_70B, "q4_0")
    assert q4_0 == round(fp16 * (0.5625 / 2.0))


# --- Concurrency clamping ---


def test_concurrency_zero_gives_zero_kv_cache_but_still_estimates():
    estimate = estimate_memory(_LLAMA_8B, _A100_80, "fp16", 4096, concurrency=0)
    assert estimate is not None
    assert estimate.kv_cache_bytes == 0


def test_negative_concurrency_clamped_to_zero():
    result = evaluate_fit(_LLAMA_8B, _A100_80, "fp16", 4096, concurrency=-3)
    assert result.concurrency == 0


# --- Warnings ---


def test_context_exceeding_max_produces_warning_not_error():
    result = evaluate_fit(_GEMMA_9B, _A100_80, "fp16", 100_000)
    assert result.error is None
    assert any("exceeds" in w for w in result.warnings)


def test_moe_model_produces_mixture_of_experts_warning():
    result = evaluate_fit(_MIXTRAL, _A100_80, "q4_k_m", 4096)
    assert any("mixture-of-experts" in w for w in result.warnings)


def test_tensor_parallel_warning_when_kv_heads_not_divisible():
    # _LLAMA_70B has n_kv_heads=8, which does not divide evenly across 3.
    result = evaluate_fit(_LLAMA_70B, _THREE_DEVICE, "q4_k_m", 4096)
    assert any("Tensor parallelism" in w for w in result.warnings)


def test_tensor_parallel_warning_absent_when_divisible():
    # n_kv_heads=8 divides evenly across 8 devices.
    result = evaluate_fit(_LLAMA_70B, _H100_X8, "q4_k_m", 4096)
    assert not any("Tensor parallelism" in w for w in result.warnings)


def test_unified_memory_produces_advisory_warning():
    result = evaluate_fit(_LLAMA_8B, _M2_ULTRA, "q4_k_m", 4096)
    assert any("Unified memory" in w for w in result.warnings)
    assert framework_overhead_bytes(_M2_ULTRA) == 512 * 1024 * 1024


# --- Fit at scale: DeepSeek V3 across two real hardware pools ---


def test_deepseek_v3_fp8_does_not_fit_eight_h100s():
    # ~625 GiB of weights at fp8 vs ~576 GiB usable on 8x H100 80GB.
    result = evaluate_fit(_DEEPSEEK_V3, _H100_X8, "fp8", 4096)
    assert result.fits is False


def test_deepseek_v3_fp8_fits_eight_h200s():
    # 8x H200 141GB has much more headroom.
    result = evaluate_fit(_DEEPSEEK_V3, _H200_X8, "fp8", 4096)
    assert result.fits is True


# --- Edge cases: must never raise ---


def test_zero_vram_hardware_gives_no_utilization_pct():
    result = evaluate_fit(_LLAMA_8B, _ZERO_VRAM, "q4_k_m", 4096)
    assert result.utilization_pct is None
    assert result.fits is False
    assert result.max_concurrent_requests == 0
    assert result.headroom_bytes is not None
    assert result.headroom_bytes < 0


def test_evaluate_fit_missing_architecture():
    result = evaluate_fit(None, _A100_80, "q4_k_m", 4096)
    assert result.error is not None
    assert result.estimate is None


def test_evaluate_fit_missing_hardware():
    result = evaluate_fit(_LLAMA_8B, None, "q4_k_m", 4096)
    assert result.error is not None
    assert result.estimate is None


def test_evaluate_fit_unknown_quantization():
    result = evaluate_fit(_LLAMA_8B, _A100_80, "nope", 4096)
    assert result.error is not None
    assert result.estimate is None


def test_evaluate_fit_unknown_kv_cache_dtype():
    result = evaluate_fit(_LLAMA_8B, _A100_80, "q4_k_m", 4096, kv_cache_dtype="nope")
    assert result.error is not None


def test_evaluate_fit_zero_context_length():
    result = evaluate_fit(_LLAMA_8B, _A100_80, "q4_k_m", 0)
    assert result.error is not None
    assert result.estimate is None


def test_evaluate_fit_negative_context_length():
    result = evaluate_fit(_LLAMA_8B, _A100_80, "q4_k_m", -100)
    assert result.error is not None


def test_evaluate_fit_bad_mla_data_missing_kv_lora_rank():
    result = evaluate_fit(_DEEPSEEK_V3_BAD_MLA, _A100_80, "q4_k_m", 4096)
    assert result.error is not None
    assert "kv_lora_rank" in result.error


def test_weight_bytes_zero_params_returns_none():
    zero_params = ModelArchitecture(
        id="test:zero",
        display_name="Zero",
        family="Test",
        vendor="Test",
        total_params=0,
        active_params=0,
        n_layers=1,
        n_attention_heads=1,
        n_kv_heads=1,
        head_dim=1,
        hidden_size=1,
        max_context_length=1,
        attention_type="gqa",
    )
    assert weight_bytes(zero_params, "q4_k_m") is None


def test_max_concurrent_requests_none_when_kv_cache_zero():
    # A degenerate architecture whose KV formula legitimately evaluates to 0
    # bytes/token (n_kv_heads=0) can't be divided into -- returns None, not
    # a crash or a misleading 0.
    degenerate = ModelArchitecture(
        id="test:degenerate",
        display_name="Degenerate",
        family="Test",
        vendor="Test",
        total_params=1_000_000_000,
        active_params=1_000_000_000,
        n_layers=1,
        n_attention_heads=1,
        n_kv_heads=0,
        head_dim=128,
        hidden_size=128,
        max_context_length=4096,
        attention_type="gqa",
    )
    assert (
        max_concurrent_requests(degenerate, _A100_80, "q4_k_m", 4096) is None
    )
