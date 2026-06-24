"""Tests for tokenization backends."""

from norefund.core.models_registry import get_model
from norefund.core.tokenization import TikTokenBackend, get_tokenizer


def test_tiktoken_backend_count_positive():
    backend = TikTokenBackend("gpt-4o")
    assert backend.count("Hello world") > 0


def test_tiktoken_backend_empty_string():
    backend = TikTokenBackend("gpt-4o")
    assert backend.count("") == 0


def test_tiktoken_backend_longer_text_more_tokens():
    backend = TikTokenBackend("gpt-4o")
    short = backend.count("Hi")
    long = backend.count("Hi " * 100)
    assert long > short


def test_tiktoken_fallback_unknown_model():
    # Should not raise — falls back to cl100k_base
    backend = TikTokenBackend("unknown-model-xyz")
    assert backend.count("test") > 0


def test_get_tokenizer_returns_tiktoken_for_gpt4o():
    model = get_model("openai:gpt-4o")
    backend = get_tokenizer(model)
    assert isinstance(backend, TikTokenBackend)


def test_get_tokenizer_unknown_backend_raises():
    from norefund.core.models_registry import ModelInfo
    bad_model = ModelInfo(
        id="bad:model",
        display_name="Bad",
        provider="Test",
        tokenizer_backend="unsupported",
        tokenizer_name="none",
        context_window=1000,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    )
    try:
        get_tokenizer(bad_model)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
