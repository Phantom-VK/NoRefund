"""Load and query self-host hardware targets from YAML.

Mirrors architectures.py / models_registry.py's load/cache/get/list shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from norefund.core.paths import bundled_resource

_DEFAULT_HARDWARE_PATH = bundled_resource("config/hardware.yaml")

_cache: dict[Path, dict[str, HardwareTarget]] = {}

HardwareCategory = Literal["datacenter_gpu", "aws", "gcp", "azure", "consumer"]
MemoryKind = Literal["discrete", "unified"]


@dataclass(frozen=True)
class HardwareTarget:
    id: str
    display_name: str
    category: HardwareCategory
    vendor: str
    accelerator: str
    device_count: int
    memory_gib_per_device: float
    memory_kind: MemoryKind
    usable_memory_fraction: float
    notes: str | None = None


def load_hardware(path: Path = _DEFAULT_HARDWARE_PATH) -> dict[str, HardwareTarget]:
    key = path.resolve()
    if key in _cache:
        return _cache[key]
    if not path.exists():
        raise FileNotFoundError(f"Hardware registry not found: {path}")
    try:
        raw: list[dict] = yaml.safe_load(path.read_text())
        if not isinstance(raw, list):
            raise ValueError("Hardware YAML must be a list of entries.")
        hardware = {entry["id"]: HardwareTarget(**entry) for entry in raw}
        _cache[key] = hardware
        return hardware
    except (yaml.YAMLError, TypeError, KeyError) as exc:
        raise ValueError(f"Failed to parse hardware registry '{path}': {exc}") from exc


def get_hardware(
    hardware_id: str, path: Path = _DEFAULT_HARDWARE_PATH
) -> HardwareTarget:
    hardware = load_hardware(path)
    if hardware_id not in hardware:
        raise ValueError(
            f"Unknown hardware '{hardware_id}'. "
            f"Available: {', '.join(sorted(hardware.keys()))}"
        )
    return hardware[hardware_id]


def find_hardware(
    hardware_id: str, path: Path = _DEFAULT_HARDWARE_PATH
) -> HardwareTarget | None:
    """Like get_hardware, but returns None instead of raising when missing."""
    return load_hardware(path).get(hardware_id)


def list_hardware(path: Path = _DEFAULT_HARDWARE_PATH) -> list[HardwareTarget]:
    return list(load_hardware(path).values())


def list_hardware_by_category(
    category: str, path: Path = _DEFAULT_HARDWARE_PATH
) -> list[HardwareTarget]:
    return [h for h in list_hardware(path) if h.category == category]
