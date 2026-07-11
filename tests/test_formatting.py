"""Tests for pure GUI formatting helpers."""

from norefund.core.models_registry import ModelInfo
from norefund.gui.formatting import fmt_bytes, model_label

_BASE_KWARGS = dict(
    id="test:model",
    display_name="Test Model",
    provider="TestCo",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=1000,
    input_price_per_million=0.0,
    output_price_per_million=0.0,
)


def test_model_label_shows_display_name_and_provider():
    model = ModelInfo(**_BASE_KWARGS)
    assert model_label(model) == "Test Model  ·  TestCo"


def test_model_label_flags_approximate_tokenizer():
    model = ModelInfo(**_BASE_KWARGS, tokenizer_is_approximate=True)
    label = model_label(model)
    assert "Test Model" in label
    assert "approx" in label.lower()


def test_model_label_does_not_flag_real_tokenizer():
    model = ModelInfo(**_BASE_KWARGS, tokenizer_is_approximate=False)
    assert "approx" not in model_label(model).lower()


def test_fmt_bytes_none_is_dash():
    assert fmt_bytes(None) == "—"


def test_fmt_bytes_bytes():
    assert fmt_bytes(500) == "500 B"


def test_fmt_bytes_kilobytes():
    assert fmt_bytes(2048) == "2.0 KB"


def test_fmt_bytes_megabytes():
    assert fmt_bytes(5 * 1024 * 1024) == "5.0 MB"


def test_fmt_bytes_gigabytes():
    assert fmt_bytes(3 * 1024 * 1024 * 1024) == "3.0 GB"
