"""Aggregation: directory stats and the top-level ResourceReport builder."""

from __future__ import annotations

from pathlib import Path

from norefund.core import paths
from norefund.core.models_registry import ModelInfo
from norefund.core.resources.probe import _group_by_resource, probe_hf, probe_tiktoken
from norefund.core.resources.types import ManagedDir, ResourceReport, TokenizerResource


def dir_stats(path: Path) -> tuple[int, int]:
    """Return (total_bytes, file_count) for a directory tree, tolerating
    per-file errors (permissions, races)."""
    if not path.exists():
        return 0, 0
    total = 0
    count = 0
    for entry in path.rglob("*"):
        try:
            if entry.is_file():
                total += entry.stat().st_size
                count += 1
        except OSError:
            continue
    return total, count


def _managed_dir(label: str, path: Path) -> ManagedDir:
    exists = path.exists()
    size, count = dir_stats(path) if exists else (0, 0)
    return ManagedDir(
        label=label, path=path, exists=exists, size_bytes=size, file_count=count
    )


def build_resource_report(models: list[ModelInfo] | None = None) -> ResourceReport:
    grouped = _group_by_resource(models)

    tokenizers: list[TokenizerResource] = []
    for (backend, name), model_ids in grouped.items():
        if backend == "tiktoken":
            resource = probe_tiktoken(name)
        else:
            resource = probe_hf(name)
        tokenizers.append(
            TokenizerResource(
                key=resource.key,
                backend=resource.backend,
                name=resource.name,
                model_ids=tuple(model_ids),
                is_cached=resource.is_cached,
                cache_path=resource.cache_path,
                size_bytes=resource.size_bytes,
                source_url=resource.source_url,
                notes=resource.notes,
            )
        )

    from norefund.logging_config import LEGACY_LOG_DIR

    dirs = [
        _managed_dir("Settings", paths.app_config_dir()),
        _managed_dir("Logs", paths.app_log_dir()),
        _managed_dir("tiktoken cache", paths.tiktoken_cache_dir()),
        _managed_dir("HuggingFace cache", paths.hf_cache_dir()),
    ]
    if LEGACY_LOG_DIR.exists():
        dirs.append(_managed_dir("Legacy logs (pre-1.0)", LEGACY_LOG_DIR))

    total_tokenizer_bytes = sum(t.size_bytes or 0 for t in tokenizers)

    return ResourceReport(
        tokenizers=tokenizers, dirs=dirs, total_tokenizer_bytes=total_tokenizer_bytes
    )
