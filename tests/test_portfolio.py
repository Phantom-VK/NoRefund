"""Tests for pure portfolio-projection functions."""

from norefund.core.models_registry import ModelInfo
from norefund.core.portfolio import cheapest_that_fits, project_costs

# Reusable dummy models for projection tests
_CHEAP_MODEL = ModelInfo(
    id="test:cheap",
    display_name="Cheap Model",
    provider="Test",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=128_000,
    input_price_per_million=1.0,
    output_price_per_million=2.0,
)
_EXPENSIVE_MODEL = ModelInfo(
    id="test:expensive",
    display_name="Expensive Model",
    provider="Test",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=128_000,
    input_price_per_million=10.0,
    output_price_per_million=20.0,
)
_SMALL_CONTEXT_MODEL = ModelInfo(
    id="test:small-context",
    display_name="Small Context Model",
    provider="Test",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=4_000,
    input_price_per_million=1.0,
    output_price_per_million=2.0,
)


def test_project_costs_monthly_frequency_matches_cost_per_run():
    # 1 run at "monthly" == exactly one call's worth of cost per month.
    # 1M input tokens @ $1/M + 1M output tokens @ $2/M = $3 per run.
    projections = project_costs(
        {"test:cheap": 1_000_000}, 1_000_000, 1, "monthly", [_CHEAP_MODEL]
    )
    assert len(projections) == 1
    p = projections[0]
    assert p.cost_per_run == 3.0
    assert p.monthly_cost == 3.0
    assert p.annual_cost == 36.0


def test_project_costs_daily_frequency_multiplies_by_30():
    # 10 runs/day * 30 days/month = 300 runs/month.
    projections = project_costs(
        {"test:cheap": 1_000_000}, 1_000_000, 10, "daily", [_CHEAP_MODEL]
    )
    p = projections[0]
    assert p.monthly_cost == 3.0 * 300
    assert p.annual_cost == p.monthly_cost * 12


def test_project_costs_weekly_frequency():
    # 7 runs/week * (30/7) weeks/month = 30 runs/month.
    projections = project_costs(
        {"test:cheap": 1_000_000}, 1_000_000, 7, "weekly", [_CHEAP_MODEL]
    )
    p = projections[0]
    assert round(p.monthly_cost, 6) == round(3.0 * 30, 6)


def test_project_costs_skips_model_with_no_corpus_entry():
    # test:expensive has no entry in corpus_tokens -- should be silently
    # skipped, not raised on.
    projections = project_costs(
        {"test:cheap": 1_000}, 100, 1, "monthly", [_CHEAP_MODEL, _EXPENSIVE_MODEL]
    )
    assert [p.model.id for p in projections] == ["test:cheap"]


def test_project_costs_fits_in_context_true():
    projections = project_costs(
        {"test:cheap": 1_000}, 100, 1, "monthly", [_CHEAP_MODEL]
    )
    assert projections[0].fits_in_context is True


def test_project_costs_fits_in_context_false():
    projections = project_costs(
        {"test:small-context": 5_000}, 100, 1, "monthly", [_SMALL_CONTEXT_MODEL]
    )
    assert projections[0].fits_in_context is False


def test_project_costs_empty_models_returns_empty():
    assert project_costs({}, 100, 1, "monthly", []) == []


def test_project_costs_zero_runs_gives_zero_monthly_cost():
    projections = project_costs(
        {"test:cheap": 1_000_000}, 1_000_000, 0, "monthly", [_CHEAP_MODEL]
    )
    assert projections[0].monthly_cost == 0.0
    assert projections[0].cost_per_run == 3.0  # per-run cost is unaffected


def test_cheapest_that_fits_picks_lower_monthly_cost():
    projections = project_costs(
        {"test:cheap": 1_000, "test:expensive": 1_000},
        100,
        1,
        "monthly",
        [_CHEAP_MODEL, _EXPENSIVE_MODEL],
    )
    cheapest = cheapest_that_fits(projections)
    assert cheapest is not None
    assert cheapest.model.id == "test:cheap"


def test_cheapest_that_fits_excludes_models_that_overflow():
    projections = project_costs(
        {"test:small-context": 5_000, "test:cheap": 5_000},
        100,
        1,
        "monthly",
        [_SMALL_CONTEXT_MODEL, _CHEAP_MODEL],
    )
    cheapest = cheapest_that_fits(projections)
    assert cheapest is not None
    assert cheapest.model.id == "test:cheap"


def test_cheapest_that_fits_returns_none_when_nothing_fits():
    projections = project_costs(
        {"test:small-context": 5_000}, 100, 1, "monthly", [_SMALL_CONTEXT_MODEL]
    )
    assert cheapest_that_fits(projections) is None
