"""Service layer — orchestrates parsing, tokenisation and costing.

Includes structured logging so all key operations are captured as
JSON log lines in the per-user log directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from norefund.core.costing import (
    context_usage_pct,
    fits_in_context,
    input_cost,
    min_chunks,
)
from norefund.core.models_registry import get_model, load_models
from norefund.core.parsing import extract_text
from norefund.core.tokenization import get_tokenizer
from norefund.logging_config import get_logger

_LOG = get_logger(__name__)
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


def list_model_ids() -> list[str]:
    """Return all known model IDs for use in CLI help / validation."""
    return list(load_models().keys())


def analyze_file(path: Path, model_id: str) -> AnalysisResult:
    models = load_models()
    if model_id not in models:
        raise ValueError(
            f"Unknown model '{model_id}'. "
            f"Available: {', '.join(sorted(models.keys()))}"
        )
    model = models[model_id]
    tokenizer = get_tokenizer(model)
    text = extract_text(path)

    tokens = tokenizer.count(text)

    result = AnalysisResult(
        file_path=str(path),
        model_id=model_id,
        char_count=len(text),
        word_count=len(text.split()),
        token_count=tokens,
        context_usage_pct=context_usage_pct(tokens, model.context_window),
        fits_in_context=fits_in_context(tokens, model.context_window),
        min_chunks_needed=min_chunks(tokens, model.context_window),
        estimated_input_cost=input_cost(tokens, model),
    )

    _LOG.info(
        "analysed_file",
        extra={
            "ctx": {
                "path": result.file_path,
                "model": result.model_id,
                "tokens": result.token_count,
                "context_pct": result.context_usage_pct,
                "fits": result.fits_in_context,
                "chunks": result.min_chunks_needed,
                "input_cost": result.estimated_input_cost,
            }
        },
    )

    return result


def analyze_folder(folder: Path, model_id: str) -> list[AnalysisResult]:
    """Analyze all supported files in a folder. Skips files that fail; logs each skip."""
    results = []
    for f in sorted(folder.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in _SUPPORTED:
            continue
        try:
            results.append(analyze_file(f, model_id))
        except Exception as exc:
            _LOG.warning(
                "skipped_file",
                extra={"ctx": {"path": str(f), "reason": str(exc)}},
            )
    _LOG.info(
        "analysed_folder",
        extra={
            "ctx": {
                "folder": str(folder),
                "model": model_id,
                "files": len(results),
            }
        },
    )
    return results
