"""Tests for pure GUI formatting helpers."""

from norefund.core.models_registry import ModelInfo
from norefund.gui.formatting import model_label

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
