"""Service layer — orchestrates parsing, tokenisation and costing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from norefund.core.costing import (
    context_usage_pct,
    fits_in_context,
    input_cost,
    min_chunks,
)
from norefund.core.models_registry import get_model
from norefund.core.parsing import parse_file
from norefund.core.tokenization import get_tokenizer

# Supported extensions (lower-cased)
_SUPPORTED = {".txt", ".md", ".pdf", ".pptx", ".docx", ".py", ".json"}


@dataclass
class AnalysisResult:
    file_path: str
    model_id: str
    char_count: int
    word_count: int
    token_count: int
    context_usage_pct: float
    fits_in_context: bool
    min_chunks_needed: int
    estimated_input_cost: float


def analyze_file(path: Path, model_id: str) -> AnalysisResult:
    model     = get_model(model_id)
    tokenizer = get_tokenizer(model)
    text      = parse_file(path)

    tokens = tokenizer.count(text)

    return AnalysisResult(
        file_path            = str(path),
        model_id             = model_id,
        char_count           = len(text),
        word_count           = len(text.split()),
        token_count          = tokens,
        context_usage_pct    = context_usage_pct(tokens, model.context_window),
        fits_in_context      = fits_in_context(tokens, model.context_window),
        min_chunks_needed    = min_chunks(tokens, model.context_window),
        estimated_input_cost = input_cost(tokens, model),
    )


def analyze_folder(folder: Path, model_id: str) -> List[AnalysisResult]:
    results = []
    for f in sorted(folder.rglob("*")):
        if f.is_file() and f.suffix.lower() in _SUPPORTED:
            results.append(analyze_file(f, model_id))
    return results
