"""PDF report renderer, built with ReportLab's Platypus layout engine.

reportlab is imported function-locally (heavy third-party import
convention) so importing this module has no cost unless a PDF is actually
requested.
"""

from __future__ import annotations

import io

from norefund.core.report._format import fmt_bytes, fmt_cost, fmt_num, fmt_pct
from norefund.core.report.model import ReportModel

_PRIMARY = "#00b894"
_DESTRUCTIVE = "#ef4444"
_MUTED = "#6b7280"
_BORDER = "#e2e2e4"


def _styles():
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontSize=20, spaceAfter=4
        )
    )
    base.add(
        ParagraphStyle(
            "Meta", parent=base["Normal"], textColor=_MUTED, fontSize=9,
            spaceAfter=18,
        )
    )
    base.add(
        ParagraphStyle(
            "SectionHeading", parent=base["Heading2"], spaceBefore=16,
            spaceAfter=8,
        )
    )
    base.add(
        ParagraphStyle("Verdict", parent=base["Normal"], fontSize=11, spaceAfter=6)
    )
    return base


def _table(header: list[str], rows: list[list[str]]):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    data = [header, *rows]
    table = Table(data, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(_MUTED)),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, colors.HexColor(_BORDER)),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor(_BORDER)),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _analysis_flowables(report: ReportModel, styles) -> list:
    from reportlab.platypus import Paragraph, Spacer

    assert report.analysis is not None
    rows = []
    for r in report.analysis:
        if r.error:
            rows.append([r.file_path, r.error, "", "", "", ""])
            continue
        rows.append(
            [
                r.file_path,
                fmt_num(r.token_count),
                fmt_pct(r.context_usage_pct),
                "Fits" if r.fits_in_context else "Does not fit",
                str(r.min_chunks_needed),
                fmt_cost(r.estimated_input_cost),
            ]
        )
    table = _table(
        ["File", "Tokens", "Context %", "Fits", "Chunks", "Input cost"], rows
    )
    return [
        Paragraph("Analysis", styles["SectionHeading"]),
        table,
        Spacer(1, 8),
    ]


def _comparison_flowables(report: ReportModel, styles) -> list:
    from reportlab.platypus import Paragraph, Spacer

    assert report.comparison is not None
    rows = []
    for r in report.comparison.results:
        if r.error:
            rows.append([r.model.display_name, r.error, "", "", "", ""])
            continue
        rows.append(
            [
                r.model.display_name,
                r.model.provider,
                fmt_num(r.token_count),
                fmt_pct(r.context_usage_pct),
                "Fits" if r.fits_in_context else "Does not fit",
                fmt_cost(r.total_cost),
            ]
        )
    table = _table(
        ["Model", "Provider", "Tokens", "Context %", "Fits", "Total cost"], rows
    )
    return [
        Paragraph(
            f"Comparison — {report.comparison.source_label}",
            styles["SectionHeading"],
        ),
        table,
        Spacer(1, 8),
    ]


def _fit_flowables(report: ReportModel, styles) -> list:
    from reportlab.lib import colors
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, Spacer

    fit = report.fit
    assert fit is not None
    flowables = [Paragraph("Fit Check", styles["SectionHeading"])]

    if fit.error is not None:
        flowables.append(Paragraph(fit.error, styles["Verdict"]))
        return [*flowables, Spacer(1, 8)]

    assert fit.estimate is not None
    model_name = report.fit_architecture_name or fit.architecture_id
    hw_name = report.fit_hardware_name or fit.hardware_id
    quant_name = report.fit_quantization_name or fit.quantization
    kv_name = report.fit_kv_cache_name or fit.kv_cache_dtype

    verdict_color = _PRIMARY if fit.fits else _DESTRUCTIVE
    verdict_text = "Fits on this hardware" if fit.fits else "Does not fit"
    flowables.append(
        Paragraph(
            f'<font color="{verdict_color}"><b>{model_name} on {hw_name}: '
            f"{verdict_text}</b></font> ({fmt_pct(fit.utilization_pct)} "
            "utilization)",
            styles["Verdict"],
        )
    )
    flowables.append(
        Paragraph(
            f"Quantization: {quant_name} &middot; KV cache: {kv_name} &middot; "
            f"Context: {fmt_num(fit.context_length)} tokens &middot; "
            f"Concurrency: {fit.concurrency}",
            styles["Normal"],
        )
    )
    table = _table(
        ["Weights", "KV cache", "Activations", "Overhead", "Total", "Headroom"],
        [
            [
                fmt_bytes(fit.estimate.weights_bytes),
                fmt_bytes(fit.estimate.kv_cache_bytes),
                fmt_bytes(fit.estimate.activation_bytes),
                fmt_bytes(fit.estimate.framework_overhead_bytes),
                fmt_bytes(fit.estimate.total_bytes),
                fmt_bytes(fit.headroom_bytes),
            ]
        ],
    )
    flowables.append(Spacer(1, 6))
    flowables.append(table)
    if fit.warnings:
        flowables.append(Spacer(1, 6))
        flowables.append(
            ListFlowable(
                [ListItem(Paragraph(w, styles["Normal"])) for w in fit.warnings],
                bulletColor=colors.HexColor("#f59e0b"),
            )
        )
    flowables.append(Spacer(1, 8))
    return flowables


def _portfolio_flowables(report: ReportModel, styles) -> list:
    from reportlab.platypus import Paragraph, Spacer

    assert report.portfolio is not None
    rows = [
        [
            p.model.display_name,
            "Fits" if p.fits_in_context else "Does not fit",
            fmt_cost(p.cost_per_run),
            fmt_cost(p.monthly_cost),
            fmt_cost(p.annual_cost),
        ]
        for p in report.portfolio
    ]
    table = _table(["Model", "Fits", "Per run", "Monthly", "Annual"], rows)
    title = "Portfolio projection"
    if report.portfolio_frequency_label:
        title += f" — {report.portfolio_frequency_label}"
    return [Paragraph(title, styles["SectionHeading"]), table, Spacer(1, 8)]


def render_pdf(report: ReportModel) -> bytes:
    """Render `report` to PDF bytes. Never raises on empty sections -- a
    ReportModel with no content still produces a valid one-page PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=report.title,
    )

    story = [
        Paragraph(report.title, styles["ReportTitle"]),
        Paragraph(
            f'Generated {report.generated_at.strftime("%Y-%m-%d %H:%M")} '
            "&middot; NoRefund &mdash; analysis stayed local, this report "
            "was generated entirely offline.",
            styles["Meta"],
        ),
    ]
    if report.analysis:
        story += _analysis_flowables(report, styles)
    if report.comparison is not None:
        story += _comparison_flowables(report, styles)
    if report.fit is not None:
        story += _fit_flowables(report, styles)
    if report.portfolio:
        story += _portfolio_flowables(report, styles)
    if len(story) == 2:
        story.append(Spacer(1, 8))
        story.append(Paragraph("No data to report.", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()
