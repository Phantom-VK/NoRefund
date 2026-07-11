"""Pure string builders for exporting analysis/comparison results.

No I/O here — callers write the returned string to disk themselves.
"""

from __future__ import annotations

import csv
import io

from norefund.core.compare import CompareReport
from norefund.core.service import AnalysisResult

_APPROX_MARKER = "~"


def comparison_to_csv(report: CompareReport) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Model",
            "Provider",
            "Tokens",
            "Context %",
            "Fits",
            "Chunks",
            "Input Cost",
            "Output Cost",
            "Total Cost",
            "Error",
        ]
    )
    for r in report.results:
        tokens = (
            f"{_APPROX_MARKER}{r.token_count}"
            if r.tokenizer_is_approximate
            else r.token_count
        )
        writer.writerow(
            [
                r.model.display_name,
                r.model.provider,
                tokens,
                "" if r.context_usage_pct is None else f"{r.context_usage_pct:.2f}",
                "Yes" if r.fits_in_context else "No",
                r.min_chunks_needed,
                f"{r.input_cost:.6f}",
                f"{r.output_cost:.6f}",
                f"{r.total_cost:.6f}",
                r.error or "",
            ]
        )
    return buf.getvalue()


def comparison_to_markdown(report: CompareReport) -> str:
    if not report.results:
        return f"# Comparison — {report.source_label}\n\nNo results.\n"

    lines = [
        f"# Comparison — {report.source_label}",
        "",
        "`~` marks approximate token counts (no exact local tokenizer).",
        "",
        "| Model | Provider | Tokens | Context % | Fits | Chunks "
        "| Input $ | Output $ | Total $ |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report.results:
        if r.error:
            lines.append(
                f"| {r.model.display_name} | {r.model.provider} "
                f"| — | — | — | — | — | — | error: {r.error} |"
            )
            continue
        tokens = (
            f"{_APPROX_MARKER}{r.token_count:,}"
            if r.tokenizer_is_approximate
            else f"{r.token_count:,}"
        )
        pct = "—" if r.context_usage_pct is None else f"{r.context_usage_pct:.1f}%"
        fits = "✓" if r.fits_in_context else "✗"
        lines.append(
            f"| {r.model.display_name} | {r.model.provider} | {tokens} | {pct} | "
            f"{fits} | {r.min_chunks_needed} | {r.input_cost:.4f} | "
            f"{r.output_cost:.4f} | {r.total_cost:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


def analysis_results_to_csv(results: list[AnalysisResult]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "File",
            "Model",
            "Tokens",
            "Context %",
            "Fits",
            "Chunks",
            "Input Cost",
            "Words",
            "Chars",
            "Error",
        ]
    )
    for r in results:
        writer.writerow(
            [
                r.file_path,
                r.model_id,
                r.token_count,
                "" if r.context_usage_pct is None else f"{r.context_usage_pct:.2f}",
                "Yes" if r.fits_in_context else "No",
                r.min_chunks_needed,
                f"{r.estimated_input_cost:.6f}",
                r.word_count,
                r.char_count,
                r.error or "",
            ]
        )
    return buf.getvalue()


def analysis_results_to_markdown(results: list[AnalysisResult]) -> str:
    if not results:
        return "# Analysis results\n\nNo results.\n"

    lines = [
        "# Analysis results",
        "",
        "| File | Tokens | Context % | Fits | Chunks | Input $ | Words | Chars |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        if r.error:
            lines.append(
                f"| {r.file_path} | — | — | — | — | — | — | error: {r.error} |"
            )
            continue
        pct = "—" if r.context_usage_pct is None else f"{r.context_usage_pct:.1f}%"
        fits = "✓" if r.fits_in_context else "✗"
        lines.append(
            f"| {r.file_path} | {r.token_count:,} | {pct} | {fits} | "
            f"{r.min_chunks_needed} | {r.estimated_input_cost:.4f} | "
            f"{r.word_count:,} | {r.char_count:,} |"
        )
    lines.append("")
    return "\n".join(lines)
