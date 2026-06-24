"""Orchestrates parsing → tokenization → costing into a single AnalysisResult."""

from dataclasses import dataclass
from pathlib import Path

from norefund.core import costing, parsing, tokenization
from norefund.core.models_registry import get_model


@dataclass
class AnalysisResult:
    file_path: str
    file_type: str
    char_count: int
    word_count: int
    token_count: int
    context_window: int
    context_usage_pct: float
    fits_in_context: bool
    min_chunks_needed: int
    estimated_input_cost: float
    model_id: str


def analyze_file(path: Path, model_id: str) -> AnalysisResult:
    """Full analysis pipeline for a single file."""
    model = get_model(model_id)
    text = parsing.extract_text(path)
    tokens = tokenization.get_tokenizer(model).count(text)

    return AnalysisResult(
        file_path=str(path),
        file_type=path.suffix.lower(),
        char_count=len(text),
        word_count=len(text.split()),
        token_count=tokens,
        context_window=model.context_window,
        context_usage_pct=costing.context_usage_pct(tokens, model.context_window),
        fits_in_context=costing.fits_in_context(tokens, model.context_window),
        min_chunks_needed=costing.min_chunks(tokens, model.context_window),
        estimated_input_cost=costing.input_cost(tokens, model),
        model_id=model_id,
    )


def analyze_folder(folder: Path, model_id: str) -> list[AnalysisResult]:
    """Analyze all supported files in a folder recursively."""
    files = [
        f
        for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in parsing.SUPPORTED_EXTENSIONS
    ]
    return [analyze_file(f, model_id) for f in files]
