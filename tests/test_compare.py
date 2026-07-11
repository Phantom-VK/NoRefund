from __future__ import annotations

from norefund.core.compare import compare_paths, compare_text, what_if
from norefund.core.models_registry import ModelInfo


def _model(
    model_id: str,
    tokenizer_backend: str = "tiktoken",
    tokenizer_name: str = "gpt-4o",
    context_window: int = 1000,
    input_price: float = 1.0,
    output_price: float = 2.0,
    approximate: bool = False,
) -> ModelInfo:
    return ModelInfo(
        id=model_id,
        display_name=model_id,
        provider="Test",
        tokenizer_backend=tokenizer_backend,
        tokenizer_name=tokenizer_name,
        context_window=context_window,
        input_price_per_million=input_price,
        output_price_per_million=output_price,
        tokenizer_is_approximate=approximate,
    )


class _FakeTokenizer:
    call_count: dict[str, int] = {}

    def __init__(self, key: str, tokens_per_call: int = 5) -> None:
        self.key = key
        self.tokens_per_call = tokens_per_call

    def count(self, text: str) -> int:
        _FakeTokenizer.call_count[self.key] = _FakeTokenizer.call_count.get(self.key, 0) + 1
        return self.tokens_per_call


def _patch_tokenizers(monkeypatch, tokens_per_call: int = 5) -> None:
    _FakeTokenizer.call_count = {}

    def fake_get_tokenizer(model: ModelInfo):
        return _FakeTokenizer(f"{model.tokenizer_backend}:{model.tokenizer_name}", tokens_per_call)

    monkeypatch.setattr("norefund.core.compare.get_tokenizer", fake_get_tokenizer)


def test_compare_text_tokenizes_shared_encoding_only_once(monkeypatch):
    _patch_tokenizers(monkeypatch)
    models = [
        _model("openai:gpt-4o", tokenizer_name="gpt-4o"),
        _model("openai:gpt-4o-mini", tokenizer_name="gpt-4o-mini"),
    ]
    report = compare_text("hello world", models, output_tokens=100)

    assert len(report.results) == 2
    assert all(r.token_count == 5 for r in report.results)
    # Both models canonicalize to the o200k_base encoding — tokenized once.
    assert sum(_FakeTokenizer.call_count.values()) == 1


def test_compare_text_computes_costs_and_context_fit(monkeypatch):
    _patch_tokenizers(monkeypatch, tokens_per_call=500)
    model = _model("test:model", context_window=1000, input_price=2.0, output_price=4.0)
    report = compare_text("some text", [model], output_tokens=100)

    result = report.results[0]
    assert result.token_count == 500
    assert result.fits_in_context is True
    assert result.input_cost == (500 / 1_000_000) * 2.0
    assert result.output_cost == (100 / 1_000_000) * 4.0
    assert result.total_cost == result.input_cost + result.output_cost
    assert result.error is None


def test_compare_text_tokenizer_error_produces_error_row(monkeypatch):
    def raising_get_tokenizer(model):
        raise RuntimeError("not downloaded yet")

    monkeypatch.setattr("norefund.core.compare.get_tokenizer", raising_get_tokenizer)
    model = _model("test:model")
    report = compare_text("text", [model], output_tokens=10)

    result = report.results[0]
    assert result.error is not None
    assert result.token_count == 0
    assert result.total_cost == 0.0


def test_what_if_recomputes_cost_without_retokenizing(monkeypatch):
    _patch_tokenizers(monkeypatch, tokens_per_call=1000)
    model = _model("test:model", context_window=2000, output_price=10.0)
    report = compare_text("text", [model], output_tokens=100)
    original = report.results[0]

    updated = what_if(original, output_tokens=500, model=model)

    assert updated.token_count == original.token_count
    assert updated.output_tokens == 500
    assert updated.output_cost == (500 / 1_000_000) * 10.0
    # No extra tokenization call happened.
    assert sum(_FakeTokenizer.call_count.values()) == 1


def test_what_if_preserves_error_rows(monkeypatch):
    def raising_get_tokenizer(model):
        raise RuntimeError("boom")

    monkeypatch.setattr("norefund.core.compare.get_tokenizer", raising_get_tokenizer)
    model = _model("test:model")
    report = compare_text("text", [model], output_tokens=10)
    original = report.results[0]

    updated = what_if(original, output_tokens=999, model=model)

    assert updated is original


def test_compare_paths_aggregates_files_per_tokenizer(monkeypatch, tmp_path):
    _patch_tokenizers(monkeypatch, tokens_per_call=42)
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")

    model = _model("test:model")
    report = compare_paths([tmp_path], [model], output_tokens=0)

    assert report.results[0].token_count == 42
    assert sum(_FakeTokenizer.call_count.values()) == 1
    assert "2 files" in report.source_label
