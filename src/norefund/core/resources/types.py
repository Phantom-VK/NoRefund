"""Shared dataclasses/exceptions for the resources package."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class TokenizerResource:
    key: str
    backend: Literal["tiktoken", "hf"]
    name: str
    model_ids: tuple[str, ...]
    is_cached: bool
    cache_path: Path | None
    size_bytes: int | None
    source_url: str | None
    notes: str | None = None


@dataclass(frozen=True)
class ManagedDir:
    label: str
    path: Path
    exists: bool
    size_bytes: int
    file_count: int


@dataclass(frozen=True)
class ResourceReport:
    tokenizers: list[TokenizerResource]
    dirs: list[ManagedDir]
    total_tokenizer_bytes: int


class ResourceDownloadError(RuntimeError):
    """Raised when a tokenizer download fails (network, gated repo, hash mismatch)."""


class DownloadCancelled(Exception):
    """Raised internally when a caller cancels an in-progress download."""


ProgressFn = Callable[[int, int | None], None]
