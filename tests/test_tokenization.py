"""Tests for tokenization backends."""

import pytest

from norefund.core.models_registry import get_model
from norefund.core.tokenization import (
    HFTokenizerBackend,
    TikTokenBackend,
    TikTokenOfflineError,
    get_tokenizer,
)


def _reset_tiktoken_registry(monkeypatch):
    """Force tiktoken's process-wide encoding cache empty for this test.

    tiktoken caches loaded Encoding objects in a module-level dict, so a
    prior test loading the same encoding would mask our cache-miss path.
    """
    import tiktoken.registry as tiktoken_registry

    monkeypatch.setattr(tiktoken_registry, "ENCODINGS", {})


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


def test_tiktoken_backend_works_when_encoding_already_cached(monkeypatch):
    _reset_tiktoken_registry(monkeypatch)
    backend = TikTokenBackend("gpt-4o")
    assert backend.count("Hello world") > 0


def test_tiktoken_backend_raises_offline_error_when_not_cached(tmp_path, monkeypatch):
    _reset_tiktoken_registry(monkeypatch)
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    with pytest.raises(TikTokenOfflineError, match="Resources view"):
        TikTokenBackend("gpt2")


def test_tiktoken_backend_fallback_path_raises_offline_error_when_not_cached(
    tmp_path, monkeypatch
):
    _reset_tiktoken_registry(monkeypatch)
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    with pytest.raises(TikTokenOfflineError, match="Resources view"):
        TikTokenBackend("unknown-model-xyz")


def test_hf_tokenizer_backend_raises_clear_error_when_not_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    with pytest.raises(RuntimeError, match="not downloaded yet"):
        HFTokenizerBackend("deepseek-ai/DeepSeek-V3")


def test_hf_tokenizer_backend_counts_tokens_when_cached(tmp_path, monkeypatch):
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace

    vocab = {"hello": 0, "world": 1, "[UNK]": 2}
    tok = Tokenizer(WordLevel(vocab=vocab, unk_token="[UNK]"))
    tok.pre_tokenizer = Whitespace()
    fixture_path = tmp_path / "tokenizer.json"
    tok.save(str(fixture_path))

    monkeypatch.setattr(
        "huggingface_hub.hf_hub_download", lambda **kwargs: str(fixture_path)
    )

    backend = HFTokenizerBackend("fake/repo")
    assert backend.count("hello world") == 2
    assert backend.count("") == 0


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
