"""Tests for models_registry module."""

from norefund.core.models_registry import ModelInfo, get_model, list_models, load_models


def test_load_models_returns_dict():
    models = load_models()
    assert isinstance(models, dict)
    assert len(models) > 0


def test_all_models_are_model_info():
    for model in load_models().values():
        assert isinstance(model, ModelInfo)


def test_gpt4o_present():
    models = load_models()
    assert "openai:gpt-4o" in models


def test_gpt4o_fields():
    model = get_model("openai:gpt-4o")
    assert model.context_window == 128_000
    assert model.input_price_per_million == 2.50
    assert model.tokenizer_backend == "tiktoken"


def test_list_models_returns_list():
    models = list_models()
    assert isinstance(models, list)
    assert all(isinstance(m, ModelInfo) for m in models)


def test_get_model_invalid_id_raises():
    try:
        get_model("fake:nonexistent")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_free_models_have_zero_price():
    """Self-hosted models should have zero cost."""
    free_ids = ["meta:llama-3-8b", "mistral:mistral-7b"]
    for model_id in free_ids:
        m = get_model(model_id)
        assert m.input_price_per_million == 0.0
        assert m.output_price_per_million == 0.0
