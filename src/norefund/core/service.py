"""Service layer — orchestrates parsing, tokenisation and costing.

Now includes structured logging so all key operations are captured as
JSON log lines in the per-user log directory.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from norefund.core.costing import (
    context_usage_pct,
    fits_in_context,
    input_cost,
    min_chunks,
)
from norefund.core.models_registry import get_model
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
    context_usage_pct: Optional[float]   # None when context_window <= 0
    fits_in_context: bool
    min_chunks_needed: int
    estimated_input_cost: float
    error: Optional[str] = None          # Non-None means analysis failed for this file


def analyze_file(path: Path, model_id: str) -> AnalysisResult:
    """Analyse a single file and return an AnalysisResult.

    Never raises — on any parse/tokenisation error the result is returned
    with `error` set and numeric fields defaulted to 0 / None.
    """
    try:
        model     = get_model(model_id)
        tokenizer = get_tokenizer(model)
        text      = extract_text(path)
        tokens    = tokenizer.count(text)

        result = AnalysisResult(
            file_path            = str(path),
            model_id             = model_id,
            char_count           = len(text),
            word_count           = len(text.split()),
            token_count          = tokens,
            context_usage_pct    = context_usage_pct(tokens, model.context_window),
            fits_in_context      = fits_in_context(tokens, model.context_window),
            min_chunks_needed    = min_chunks(tokens, model.context_window),
            estimated_input_cost = input_cost(tokens, model),
            error                = None,
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

    except Exception as exc:  # noqa: BLE001
        _LOG.warning(
            "analyse_file_failed",
            extra={"ctx": {"path": str(path), "model": model_id, "error": str(exc)}},
        )
        return AnalysisResult(
            file_path            = str(path),
            model_id             = model_id,
            char_count           = 0,
            word_count           = 0,
            token_count          = 0,
            context_usage_pct    = None,
            fits_in_context      = False,
            min_chunks_needed    = 0,
            estimated_input_cost = 0.0,
            error                = str(exc),
        )


def analyze_folder(
    folder: Path,
    model_id: str,
    *,
    on_progress: Optional[Callable[[AnalysisResult], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> List[AnalysisResult]:
    """Analyse every supported file under *folder*.

    Args:
        folder:       Root directory to scan recursively.
        model_id:     Model to use for tokenisation and cost estimation.
        on_progress:  Optional callback invoked after each file completes
                      (result passed as argument). Used by the GUI to update
                      the log tab in real time.
        cancel_event: Optional threading.Event. When set, the loop exits
                      cleanly after the current file finishes. The GUI
                      passes this to implement a Cancel button.

    Returns:
        List of AnalysisResult — one per supported file found. Results with
        `error` set represent files that failed to parse or tokenise.
    """
    results: List[AnalysisResult] = []

    for f in sorted(folder.rglob("*")):
        if cancel_event is not None and cancel_event.is_set():
            _LOG.info(
                "analyse_folder_cancelled",
                extra={"ctx": {"folder": str(folder), "completed": len(results)}},
            )
            break

        if not (f.is_file() and f.suffix.lower() in _SUPPORTED):
            continue

        # analyze_file already catches all exceptions internally
        result = analyze_file(f, model_id)
        results.append(result)

        if on_progress is not None:
            try:
                on_progress(result)
            except Exception as cb_exc:  # noqa: BLE001
                _LOG.warning(
                    "on_progress_callback_failed",
                    extra={"ctx": {"error": str(cb_exc)}},
                )

    _LOG.info(
        "analysed_folder",
        extra={
            "ctx": {
                "folder": str(folder),
                "model": model_id,
                "files": len(results),
                "errors": sum(1 for r in results if r.error is not None),
            }
        },
    )
    return results
