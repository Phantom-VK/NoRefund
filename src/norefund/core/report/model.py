"""The single data contract report renderers (pdf.py / html.py) build from.

Every section is optional so one report can carry any subset of what the
app knows how to compute -- an analysis run, a comparison, a fit check, a
portfolio projection, or several at once. `FitResult` only carries ids
(`architecture_id`/`hardware_id`), not display names, so the GUI passes the
already-resolved display strings alongside it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from norefund.core.compare import CompareReport
from norefund.core.portfolio import PortfolioProjection
from norefund.core.selfhost import FitResult
from norefund.core.service import AnalysisResult


@dataclass(frozen=True)
class ReportModel:
    title: str
    generated_at: datetime
    analysis: list[AnalysisResult] | None = None
    comparison: CompareReport | None = None
    fit: FitResult | None = None
    fit_architecture_name: str | None = None
    fit_hardware_name: str | None = None
    fit_quantization_name: str | None = None
    fit_kv_cache_name: str | None = None
    portfolio: list[PortfolioProjection] | None = None
    portfolio_frequency_label: str | None = None

    @property
    def has_content(self) -> bool:
        return bool(self.analysis or self.comparison or self.fit or self.portfolio)
