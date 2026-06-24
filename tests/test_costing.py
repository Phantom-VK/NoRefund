"""Tests for pure costing functions."""
from src.norefund.core.costing import context_usage_pct, fits_in_context, min_chunks


def test_context_usage_pct_half():
    assert context_usage_pct(64000, 128000) == 50.0


def test_context_usage_pct_over():
    assert context_usage_pct(200000, 128000) > 100


def test_fits_in_context_true():
    assert fits_in_context(1000, 128000) is True


def test_fits_in_context_false():
    assert fits_in_context(200000, 128000) is False


def test_min_chunks_single():
    # Small doc fits in one call
    assert min_chunks(1000, 128000) == 1


def test_min_chunks_multiple():
    # 500k tokens into 128k window needs multiple calls
    assert min_chunks(500000, 128000) > 1
