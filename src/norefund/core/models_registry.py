"""Load and query the model/pricing registry from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from norefund.core.paths import bundled_resource

_DEFAULT_REGISTRY_PATH = bundled_resource("config/default_models.yaml")

_cache: dict[Path, dict[str, ModelInfo]] = {}


@dataclass
class ModelInfo:
    id: str
    display_name: str
    provider: str
    tokenizer_backend: str
    tokenizer_name: str
    context_window: int
    input_price_per_million: float
    output_price_per_million: float
    currency: str = "USD"
    docs_url: str | None = None   # Optional link to provider pricing/docs page
    tokenizer_is_approximate: bool = False  # True when no real local tokenizer exists
    # Context-tiered pricing (OpenAI, Google): prompts above this many tokens
    # bill at the long_context_* rate instead. None means flat pricing.
    long_context_threshold: int | None = None
    long_context_input_price_per_million: float | None = None
    long_context_output_price_per_million: float | None = None
    pricing_note: str | None = None  # e.g. DeepSeek's off-peak halving
    pricing_verified_on: str | None = None  # ISO date a human read the pricing page


def load_models(path: Path = _DEFAULT_REGISTRY_PATH) -> dict[str, ModelInfo]:
    key = path.resolve()
    if key in _cache:
        return _cache[key]
    if not path.exists():
        raise FileNotFoundError(f"Model registry not found: {path}")
    try:
        raw: list[dict] = yaml.safe_load(path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Registry YAML must be a list of model entries.")
        models = {entry["id"]: ModelInfo(**entry) for entry in raw}
        _cache[key] = models
        return models
    except (yaml.YAMLError, TypeError, KeyError) as exc:
        raise ValueError(f"Failed to parse model registry '{path}': {exc}") from exc


def get_model(model_id: str, path: Path = _DEFAULT_REGISTRY_PATH) -> ModelInfo:
    models = load_models(path)
    if model_id not in models:
        raise ValueError(
            f"Unknown model '{model_id}'. "
            f"Available models: {', '.join(sorted(models.keys()))}"
        )
    return models[model_id]


def list_models(path: Path = _DEFAULT_REGISTRY_PATH) -> list[ModelInfo]:
    return list(load_models(path).values())
