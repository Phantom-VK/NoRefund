"""Self-contained HTML report renderer.

Colors are copied from gui/theme.py's COLORS dict rather than imported --
core/ never imports from gui/ (see CLAUDE.md). Keep these two palettes in
sync by hand if theme.py's tokens change.
"""

from __future__ import annotations

from html import escape

from norefund.core.report._format import fmt_bytes, fmt_cost, fmt_num, fmt_pct
from norefund.core.report.model import ReportModel

_CSS = """
:root {
  --bg: #f5f6f8; --fg: #0f1117; --card: #ffffff; --border: #e2e2e4;
  --muted: #6b7280; --primary: #00b894; --destructive: #ef4444;
  --warning: #f59e0b;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111318; --fg: #e6edf3; --card: #1c2029; --border: #2a2f39;
    --muted: #7d8590; --primary: #00d4aa; --destructive: #f85149;
    --warning: #f59e0b;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 32px; background: var(--bg); color: var(--fg);
  font: 14px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
}
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 32px 0 12px; }
.meta { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px 20px; margin-bottom: 16px;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; }
tr:last-child td { border-bottom: none; }
.fit { color: var(--primary); font-weight: 600; }
.nofit { color: var(--destructive); font-weight: 600; }
.error { color: var(--destructive); }
.warnings { color: var(--warning); font-size: 13px; margin-top: 8px; }
.pill-row { display: flex; gap: 32px; flex-wrap: wrap; }
.pill .label { color: var(--muted); font-size: 12px; }
.pill .value { font-size: 18px; font-weight: 700; }
"""


def _analysis_section(report: ReportModel) -> str:
    assert report.analysis is not None
    rows = []
    for r in report.analysis:
        if r.error:
            rows.append(
                f"<tr><td>{escape(r.file_path)}</td>"
                f'<td colspan="5" class="error">{escape(r.error)}</td></tr>'
            )
            continue
        rows.append(
            f"<tr><td>{escape(r.file_path)}</td>"
            f"<td>{fmt_num(r.token_count)}</td>"
            f"<td>{fmt_pct(r.context_usage_pct)}</td>"
            f'<td class="{"fit" if r.fits_in_context else "nofit"}">'
            f'{"Fits" if r.fits_in_context else "Does not fit"}</td>'
            f"<td>{r.min_chunks_needed}</td>"
            f"<td>{fmt_cost(r.estimated_input_cost)}</td></tr>"
        )
    return (
        '<div class="card"><h2>Analysis</h2><table><thead><tr>'
        "<th>File</th><th>Tokens</th><th>Context %</th><th>Fits</th>"
        "<th>Chunks</th><th>Input cost</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table></div>"
    )


def _comparison_section(report: ReportModel) -> str:
    assert report.comparison is not None
    rows = []
    for r in report.comparison.results:
        if r.error:
            rows.append(
                f"<tr><td>{escape(r.model.display_name)}</td>"
                f'<td colspan="6" class="error">{escape(r.error)}</td></tr>'
            )
            continue
        rows.append(
            f"<tr><td>{escape(r.model.display_name)}</td>"
            f"<td>{escape(r.model.provider)}</td>"
            f"<td>{fmt_num(r.token_count)}</td>"
            f"<td>{fmt_pct(r.context_usage_pct)}</td>"
            f'<td class="{"fit" if r.fits_in_context else "nofit"}">'
            f'{"Fits" if r.fits_in_context else "Does not fit"}</td>'
            f"<td>{fmt_cost(r.total_cost)}</td></tr>"
        )
    return (
        '<div class="card"><h2>Comparison — '
        f"{escape(report.comparison.source_label)}</h2>"
        "<table><thead><tr><th>Model</th><th>Provider</th><th>Tokens</th>"
        "<th>Context %</th><th>Fits</th><th>Total cost</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _fit_section(report: ReportModel) -> str:
    fit = report.fit
    assert fit is not None
    if fit.error is not None:
        return (
            '<div class="card"><h2>Fit Check</h2>'
            f'<p class="error">{escape(fit.error)}</p></div>'
        )
    assert fit.estimate is not None
    pills = [
        ("Weights", fmt_bytes(fit.estimate.weights_bytes)),
        ("KV cache", fmt_bytes(fit.estimate.kv_cache_bytes)),
        ("Activations", fmt_bytes(fit.estimate.activation_bytes)),
        ("Framework overhead", fmt_bytes(fit.estimate.framework_overhead_bytes)),
        ("Total needed", fmt_bytes(fit.estimate.total_bytes)),
        ("Headroom", fmt_bytes(fit.headroom_bytes)),
    ]
    pill_html = "".join(
        f'<div class="pill"><div class="label">{escape(label)}</div>'
        f'<div class="value">{value}</div></div>'
        for label, value in pills
    )
    warnings_html = ""
    if fit.warnings:
        items = "".join(f"<li>{escape(w)}</li>" for w in fit.warnings)
        warnings_html = f'<ul class="warnings">{items}</ul>'
    model_name = report.fit_architecture_name or fit.architecture_id
    hw_name = report.fit_hardware_name or fit.hardware_id
    quant_name = report.fit_quantization_name or fit.quantization
    kv_name = report.fit_kv_cache_name or fit.kv_cache_dtype
    verdict_class = "fit" if fit.fits else "nofit"
    verdict_text = "Fits on this hardware" if fit.fits else "Does not fit"
    return (
        '<div class="card"><h2>Fit Check — '
        f"{escape(model_name)} on {escape(hw_name)}</h2>"
        f'<p class="{verdict_class}">{verdict_text} '
        f"({fmt_pct(fit.utilization_pct)} utilization)</p>"
        f"<p>Quantization: {escape(quant_name)} &middot; "
        f"KV cache: {escape(kv_name)} &middot; "
        f"Context: {fmt_num(fit.context_length)} tokens &middot; "
        f"Concurrency: {fit.concurrency}</p>"
        f'<div class="pill-row">{pill_html}</div>{warnings_html}</div>'
    )


def _portfolio_section(report: ReportModel) -> str:
    assert report.portfolio is not None
    period = report.portfolio_frequency_label or ""
    rows = []
    for p in report.portfolio:
        rows.append(
            f"<tr><td>{escape(p.model.display_name)}</td>"
            f'<td class="{"fit" if p.fits_in_context else "nofit"}">'
            f'{"Fits" if p.fits_in_context else "Does not fit"}</td>'
            f"<td>{fmt_cost(p.cost_per_run)}</td>"
            f"<td>{fmt_cost(p.monthly_cost)}</td>"
            f"<td>{fmt_cost(p.annual_cost)}</td></tr>"
        )
    title = "Portfolio projection"
    if period:
        title += f" — {escape(period)}"
    return (
        f'<div class="card"><h2>{title}</h2>'
        "<table><thead><tr><th>Model</th><th>Fits</th><th>Per run</th>"
        "<th>Monthly</th><th>Annual</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def render_html(report: ReportModel) -> str:
    """A self-contained HTML string -- inline CSS, no external assets, opens
    directly in any browser, light/dark aware via prefers-color-scheme."""
    sections = []
    if report.analysis:
        sections.append(_analysis_section(report))
    if report.comparison is not None:
        sections.append(_comparison_section(report))
    if report.fit is not None:
        sections.append(_fit_section(report))
    if report.portfolio:
        sections.append(_portfolio_section(report))
    if not sections:
        sections.append('<div class="card"><p>No data to report.</p></div>')

    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>{escape(report.title)}</title><style>{_CSS}</style></head>"
        f"<body><h1>{escape(report.title)}</h1>"
        f'<p class="meta">Generated '
        f'{report.generated_at.strftime("%Y-%m-%d %H:%M")} &middot; '
        "NoRefund &mdash; analysis stayed local, this report was generated "
        "entirely offline.</p>"
        f"{''.join(sections)}</body></html>"
    )
