"""Tokenizer/resource inventory: what's cached, where, how big, and downloads.

Split into submodules by concern — `probe` (read-only cache checks), `report`
(aggregation into a `ResourceReport`), `download` (the one place in `core/`
allowed to touch the network, and only via `download_tokenizer()`, which is
only ever called on explicit user action from the GUI's Resources view) —
but re-exported here as a flat namespace so `norefund.core.resources` behaves
exactly as it did as a single file.
"""

from __future__ import annotations

# Private names are re-exported via `as` aliasing (not just imported) so
# ruff treats them as intentional re-exports rather than unused imports —
# tests reach into them directly as e.g. `resources._capture_tiktoken_blob`.
from norefund.core.resources.download import _download_hf as _download_hf
from norefund.core.resources.download import _download_tiktoken as _download_tiktoken
from norefund.core.resources.download import download_tokenizer
from norefund.core.resources.probe import _GATED_HF_PREFIXES as _GATED_HF_PREFIXES
from norefund.core.resources.probe import (
    _capture_tiktoken_blob as _capture_tiktoken_blob,
)
from norefund.core.resources.probe import _CaptureBlobInfo as _CaptureBlobInfo
from norefund.core.resources.probe import _group_by_resource as _group_by_resource
from norefund.core.resources.probe import (
    canonical_tiktoken_encoding,
    probe_hf,
    probe_tiktoken,
    required_tokenizers,
)
from norefund.core.resources.report import _managed_dir as _managed_dir
from norefund.core.resources.report import build_resource_report, dir_stats
from norefund.core.resources.types import (
    DownloadCancelled,
    ManagedDir,
    ProgressFn,
    ResourceDownloadError,
    ResourceReport,
    TokenizerResource,
)

__all__ = [
    "TokenizerResource",
    "ManagedDir",
    "ResourceReport",
    "ResourceDownloadError",
    "DownloadCancelled",
    "ProgressFn",
    "canonical_tiktoken_encoding",
    "required_tokenizers",
    "probe_tiktoken",
    "probe_hf",
    "dir_stats",
    "build_resource_report",
    "download_tokenizer",
]
