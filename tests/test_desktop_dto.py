"""Dataclass -> JSON-safe conversion for the JS bridge."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from norefund.core.models_registry import ModelInfo
from norefund.core.selfhost import FitResult, MemoryEstimate
from norefund.core.service import AnalysisResult
from norefund.desktop.dto import to_jsonable


def _model() -> ModelInfo:
    return ModelInfo(
        id="gpt-4o", display_name="GPT-4o", provider="OpenAI",
        tokenizer_backend="tiktoken", tokenizer_name="o200k_base",
        context_window=128_000, input_price_per_million=2.5,
        output_price_per_million=10.0,
    )


def test_dataclass_becomes_a_dict_with_identical_field_names():
    out = to_jsonable(_model())
    assert out["id"] == "gpt-4o"
    assert out["context_window"] == 128_000
    assert out["tokenizer_is_approximate"] is False


def test_nested_dataclasses_are_converted_recursively():
    result = FitResult(
        architecture_id="a", hardware_id="h", quantization="q4_k_m",
        kv_cache_dtype="fp16", context_length=8192, concurrency=1,
        usable_memory_bytes=1, fits=True, headroom_bytes=1,
        utilization_pct=50.0, max_concurrent_requests=2,
        estimate=MemoryEstimate(1, 2, 3, 4, 5, 6),
    )
    out = to_jsonable(result)
    assert out["estimate"]["weights_bytes"] == 1


def test_tuples_become_lists_and_paths_become_strings():
    out = to_jsonable({"warnings": ("a", "b"), "p": Path("/tmp/x.pdf")})
    assert out["warnings"] == ["a", "b"]
    assert out["p"] == "/tmp/x.pdf"


def test_datetimes_become_iso_strings():
    out = to_jsonable(datetime(2026, 8, 15, 12, 0, 0))
    assert out == "2026-08-15T12:00:00"


def test_none_survives():
    out = to_jsonable(AnalysisResult(
        file_path="/tmp/a.pdf", model_id="gpt-4o", char_count=0, word_count=0,
        token_count=0, context_window=128_000, context_usage_pct=None,
        fits_in_context=True, min_chunks_needed=0, estimated_input_cost=0.0,
        error="boom",
    ))
    assert out["context_usage_pct"] is None
    assert out["error"] == "boom"


def test_output_is_actually_json_serialisable():
    json.dumps(to_jsonable([_model(), _model()]))


def test_lists_of_dataclasses_convert():
    assert len(to_jsonable([_model(), _model()])) == 2
