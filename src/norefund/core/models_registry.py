"""Load and query the model/pricing registry from YAML."""

from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULT_REGISTRY_PATH = Path(__file__).parent.parent / "config" / "default_models.yaml"

_cache: dict[str, "ModelInfo"] | None = None


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


def load_models(path: Path = _DEFAULT_REGISTRY_PATH) -> dict[str, ModelInfo]:
    global _cache
    if _cache is not None:
        return _cache
    if not path.exists():
        raise FileNotFoundError(f"Model registry not found: {path}")
    try:
        raw: list[dict] = yaml.safe_load(path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Registry YAML must be a list of model entries.")
        _cache = {entry["id"]: ModelInfo(**entry) for entry in raw}
        return _cache
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
