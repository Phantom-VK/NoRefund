"""Multi-model cost/context comparison for a single piece of text or a set
of files, tokenizing each unique tokenizer only once per source.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from norefund.core.costing import (
    context_usage_pct,
    fits_in_context,
    min_chunks,
)
from norefund.core.costing import input_cost as compute_input_cost
from norefund.core.costing import (
    output_cost as compute_output_cost,
)
from norefund.core.costing import (
    total_cost as compute_total_cost,
)
from norefund.core.models_registry import ModelInfo
from norefund.core.parsing import extract_text
from norefund.core.resources import canonical_tiktoken_encoding
from norefund.core.tokenization import get_tokenizer


@dataclass(frozen=True)
class ModelComparison:
    model: ModelInfo
    token_count: int
    context_usage_pct: float | None
    fits_in_context: bool
    min_chunks_needed: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    tokenizer_is_approximate: bool
    error: str | None = None


@dataclass(frozen=True)
class CompareReport:
    source_label: str
    results: list[ModelComparison]


def _tokenizer_key(model: ModelInfo) -> tuple[str, str]:
    """Group models sharing one tokenizer so text is tokenized once per key."""
    if model.tokenizer_backend != "tiktoken":
        return model.tokenizer_backend, model.tokenizer_name
    return "tiktoken", canonical_tiktoken_encoding(model.tokenizer_name)


def _build_comparison(
    model: ModelInfo,
    token_count: int | None,
    output_tokens: int,
    error: str | None = None,
) -> ModelComparison:
    if error is not None or token_count is None:
        return ModelComparison(
            model=model,
            token_count=0,
            context_usage_pct=None,
            fits_in_context=False,
            min_chunks_needed=0,
            output_tokens=output_tokens,
            input_cost=0.0,
            output_cost=0.0,
            total_cost=0.0,
            tokenizer_is_approximate=model.tokenizer_is_approximate,
            error=error or "Tokenizer unavailable — download it in Resources.",
        )
    return ModelComparison(
        model=model,
        token_count=token_count,
        context_usage_pct=context_usage_pct(token_count, model.context_window),
        fits_in_context=fits_in_context(token_count, model.context_window),
        min_chunks_needed=min_chunks(token_count, model.context_window),
        output_tokens=output_tokens,
        input_cost=compute_input_cost(token_count, model),
        output_cost=compute_output_cost(output_tokens, model),
        total_cost=compute_total_cost(token_count, output_tokens, model),
        tokenizer_is_approximate=model.tokenizer_is_approximate,
        error=None,
    )


def what_if(
    result: ModelComparison, output_tokens: int, model: ModelInfo
) -> ModelComparison:
    """Recompute cost fields for a new output-token assumption, without
    re-tokenizing the (unchanged) input."""
    if result.error is not None:
        return result
    return _build_comparison(model, result.token_count, output_tokens)


def compare_text(
    text: str, models: list[ModelInfo], output_tokens: int
) -> CompareReport:
    counts: dict[tuple[str, str], int] = {}
    errors: dict[tuple[str, str], str] = {}
    results: list[ModelComparison] = []

    for model in models:
        key = _tokenizer_key(model)
        if key not in counts and key not in errors:
            try:
                counts[key] = get_tokenizer(model).count(text)
            except Exception as exc:  # noqa: BLE001
                errors[key] = str(exc)

        key_error = errors.get(key)
        results.append(
            _build_comparison(model, counts.get(key), output_tokens, key_error)
        )

    label = f"{len(text):,} characters" if text else "empty text"
    return CompareReport(source_label=label, results=results)


def compare_paths(
    paths: list[Path],
    models: list[ModelInfo],
    output_tokens: int,
    *,
    on_progress: Callable[[Path], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> CompareReport:
    """Extract every file once, then tokenize the aggregated text once per
    unique tokenizer, then fan out costs per model. A directory's immediate
    contents only -- subfolders are not descended into."""
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(f for f in p.glob("*") if f.is_file()))
        else:
            files.append(p)

    combined_parts: list[str] = []
    for f in files:
        if cancel_event is not None and cancel_event.is_set():
            break
        try:
            combined_parts.append(extract_text(f))
        except Exception:  # noqa: BLE001
            pass
        if on_progress is not None:
            on_progress(f)

    text = "\n".join(combined_parts)
    report = compare_text(text, models, output_tokens)
    label = f"{len(files)} file{'s' if len(files) != 1 else ''}"
    return CompareReport(source_label=label, results=report.results)
