"""Business-volume cost projection: extend costing.py's per-call math across
a run frequency to estimate monthly/annual spend for a corpus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from norefund.core.costing import fits_in_context, total_cost
from norefund.core.models_registry import ModelInfo

RunFrequency = Literal["daily", "weekly", "monthly"]

_RUNS_PER_MONTH: dict[RunFrequency, float] = {
    "daily": 30.0,
    "weekly": 30.0 / 7.0,
    "monthly": 1.0,
}


@dataclass(frozen=True)
class PortfolioProjection:
    model: ModelInfo
    corpus_tokens: int
    fits_in_context: bool
    cost_per_run: float
    monthly_cost: float
    annual_cost: float


def project_costs(
    corpus_tokens: dict[str, int],
    output_tokens: int,
    runs_per_period: float,
    frequency: RunFrequency,
    models: list[ModelInfo],
) -> list[PortfolioProjection]:
    """One projection per model in `models` that has an entry in
    `corpus_tokens` (keyed by model.id -- tokenizers differ per model, so
    the same corpus can have a different token count per model).

    `runs_per_period` is how many runs happen at `frequency` (e.g. 100 runs
    at "daily"). Models with no corpus_tokens entry (e.g. a tokenizer that
    failed) are silently skipped, not raised on.
    """
    runs_per_month = runs_per_period * _RUNS_PER_MONTH[frequency]
    projections = []
    for model in models:
        tokens = corpus_tokens.get(model.id)
        if tokens is None:
            continue
        cost_per_run = total_cost(tokens, output_tokens, model)
        monthly_cost = cost_per_run * runs_per_month
        projections.append(
            PortfolioProjection(
                model=model,
                corpus_tokens=tokens,
                fits_in_context=fits_in_context(tokens, model.context_window),
                cost_per_run=cost_per_run,
                monthly_cost=monthly_cost,
                annual_cost=monthly_cost * 12,
            )
        )
    return projections


def cheapest_that_fits(
    projections: list[PortfolioProjection],
) -> PortfolioProjection | None:
    """The lowest monthly-cost projection among models the corpus fits in,
    or None if every model's corpus overflows its context window."""
    fitting = [p for p in projections if p.fits_in_context]
    if not fitting:
        return None
    return min(fitting, key=lambda p: p.monthly_cost)
