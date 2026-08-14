"""Load and query open-weight model architecture data from YAML.

Separate from models_registry.py (which holds pricing/context-window data)
because ModelArchitecture has different, self-host-specific fields, and
models_registry.ModelInfo(**entry) fails closed on any unknown key -- adding
these fields there would break every existing entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from norefund.core.paths import bundled_resource

_DEFAULT_ARCHITECTURE_PATH = bundled_resource("config/model_architectures.yaml")

_cache: dict[Path, dict[str, ModelArchitecture]] = {}

AttentionType = Literal["gqa", "mla"]


@dataclass(frozen=True)
class ModelArchitecture:
    id: str
    display_name: str
    family: str
    vendor: str
    total_params: int
    active_params: int
    n_layers: int
    n_attention_heads: int
    n_kv_heads: int
    head_dim: int
    hidden_size: int
    max_context_length: int
    attention_type: AttentionType
    kv_lora_rank: int = 0          # MLA only (e.g. DeepSeek V3)
    qk_rope_head_dim: int = 0      # MLA only (e.g. DeepSeek V3)
    docs_url: str | None = None


def load_architectures(
    path: Path = _DEFAULT_ARCHITECTURE_PATH,
) -> dict[str, ModelArchitecture]:
    key = path.resolve()
    if key in _cache:
        return _cache[key]
    if not path.exists():
        raise FileNotFoundError(f"Architecture registry not found: {path}")
    try:
        raw: list[dict] = yaml.safe_load(path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Architecture YAML must be a list of entries.")
        architectures = {entry["id"]: ModelArchitecture(**entry) for entry in raw}
        _cache[key] = architectures
        return architectures
    except (yaml.YAMLError, TypeError, KeyError) as exc:
        raise ValueError(
            f"Failed to parse architecture registry '{path}': {exc}"
        ) from exc


def get_architecture(
    architecture_id: str, path: Path = _DEFAULT_ARCHITECTURE_PATH
) -> ModelArchitecture:
    architectures = load_architectures(path)
    if architecture_id not in architectures:
        raise ValueError(
            f"Unknown architecture '{architecture_id}'. "
            f"Available: {', '.join(sorted(architectures.keys()))}"
        )
    return architectures[architecture_id]


def find_architecture(
    architecture_id: str, path: Path = _DEFAULT_ARCHITECTURE_PATH
) -> ModelArchitecture | None:
    """Like get_architecture, but returns None instead of raising when missing."""
    return load_architectures(path).get(architecture_id)


def list_architectures(
    path: Path = _DEFAULT_ARCHITECTURE_PATH,
) -> list[ModelArchitecture]:
    return list(load_architectures(path).values())
