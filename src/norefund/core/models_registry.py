"""Load and query the model/pricing registry from YAML."""

from dataclasses import dataclass
from pathlib import Path

import yaml

_DEFAULT_REGISTRY_PATH = Path(__file__).parent.parent / "config" / "default_models.yaml"


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
    """Load all models from YAML. Returns dict keyed by model id."""
    if not path.exists():
        raise FileNotFoundError(f"Model registry not found: {path}")
    try:
        raw: list[dict] = yaml.safe_load(path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Registry YAML must be a list of model entries.")
        return {entry["id"]: ModelInfo(**entry) for entry in raw}
    except (yaml.YAMLError, TypeError, KeyError) as exc:
        raise ValueError(f"Failed to parse model registry '{path}': {exc}") from exc


def get_model(model_id: str, path: Path = _DEFAULT_REGISTRY_PATH) -> ModelInfo:
    """Get a single model by id. Raises ValueError with helpful message if not found."""
    models = load_models(path)
    if model_id not in models:
        raise ValueError(
            f"Unknown model '{model_id}'. "
            f"Available models: {', '.join(sorted(models.keys()))}"
        )
    return models[model_id]


def list_models(path: Path = _DEFAULT_REGISTRY_PATH) -> list[ModelInfo]:
    """Return all models as a list."""
    return list(load_models(path).values())
