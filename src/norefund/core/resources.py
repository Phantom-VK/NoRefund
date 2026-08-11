"""Tokenizer/resource inventory: what's cached, where, how big, and downloads.

This is the one place in `core/` allowed to touch the network, and only via
`download_tokenizer()`, which is only ever called on explicit user action
from the GUI's Resources view.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Optional

from norefund.core import paths
from norefund.core.models_registry import ModelInfo, list_models

_LOG = logging.getLogger(__name__)

_GATED_HF_PREFIXES = ("meta-llama/",)


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


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def canonical_tiktoken_encoding(tokenizer_name: str) -> str:
    import tiktoken

    try:
        return tiktoken.encoding_name_for_model(tokenizer_name)
    except KeyError:
        return tokenizer_name


def required_tokenizers(
    models: list[ModelInfo] | None = None,
) -> list[tuple[str, str, str]]:
    """Return deduped (backend, canonical_name, model_id) rows for enumeration.

    Multiple models can share one tokenizer (e.g. every OpenAI o200k_base
    model); this collapses them by canonical name while keeping every
    model_id that maps to it, via `_group_by_resource`.
    """
    if models is None:
        models = list_models()
    rows: list[tuple[str, str, str]] = []
    for model in models:
        if model.tokenizer_backend == "tiktoken":
            name = canonical_tiktoken_encoding(model.tokenizer_name)
        else:
            name = model.tokenizer_name
        rows.append((model.tokenizer_backend, name, model.id))
    return rows


def _group_by_resource(
    models: list[ModelInfo] | None,
) -> dict[tuple[str, str], list[str]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for backend, name, model_id in required_tokenizers(models):
        grouped.setdefault((backend, name), []).append(model_id)
    return grouped


# ---------------------------------------------------------------------------
# tiktoken probe — "capture, don't load"
# ---------------------------------------------------------------------------


class _CaptureBlobInfo(Exception):
    def __init__(self, blobpath: str, expected_hash: str | None) -> None:
        super().__init__(blobpath)
        self.blobpath = blobpath
        self.expected_hash = expected_hash


def _capture_tiktoken_blob(encoding_name: str) -> tuple[str, str | None]:
    """Return (blob_url, expected_hash) for an encoding without downloading
    or parsing its vocab file.

    Works by patching tiktoken.load.read_file_cached to raise as soon as the
    encoding constructor calls it, capturing the arguments it was given.
    """
    import tiktoken.load as tiktoken_load
    import tiktoken.registry as tiktoken_registry

    tiktoken_registry._find_constructors()
    constructors = tiktoken_registry.ENCODING_CONSTRUCTORS
    if constructors is None or encoding_name not in constructors:
        raise ValueError(f"Unknown tiktoken encoding: '{encoding_name}'")

    def _capture(blobpath: str, expected_hash: str | None = None) -> bytes:
        raise _CaptureBlobInfo(blobpath, expected_hash)

    original = tiktoken_load.read_file_cached
    tiktoken_load.read_file_cached = _capture
    try:
        constructors[encoding_name]()
        raise RuntimeError(
            f"tiktoken encoding '{encoding_name}' did not call read_file_cached "
            "as expected — tiktoken internals may have changed."
        )
    except _CaptureBlobInfo as exc:
        return exc.blobpath, exc.expected_hash
    finally:
        tiktoken_load.read_file_cached = original


def probe_tiktoken(encoding_name: str) -> TokenizerResource:
    cache_dir = paths.tiktoken_cache_dir()
    try:
        blob_url, _expected_hash = _capture_tiktoken_blob(encoding_name)
        cache_key = hashlib.sha1(blob_url.encode()).hexdigest()
        cache_path = cache_dir / cache_key
        is_cached = cache_path.exists()
        size = cache_path.stat().st_size if is_cached else None
        return TokenizerResource(
            key=f"tiktoken:{encoding_name}",
            backend="tiktoken",
            name=encoding_name,
            model_ids=(),
            is_cached=is_cached,
            cache_path=cache_path if is_cached else None,
            size_bytes=size,
            source_url=blob_url,
        )
    except Exception as exc:
        _LOG.warning(
            "tiktoken_probe_failed",
            extra={"ctx": {"encoding": encoding_name, "error": str(exc)}},
        )
        return TokenizerResource(
            key=f"tiktoken:{encoding_name}",
            backend="tiktoken",
            name=encoding_name,
            model_ids=(),
            is_cached=False,
            cache_path=None,
            size_bytes=None,
            source_url=None,
            notes=f"Could not probe cache status: {exc}",
        )


# ---------------------------------------------------------------------------
# HF probe
# ---------------------------------------------------------------------------


def probe_hf(repo_id: str) -> TokenizerResource:
    from huggingface_hub import hf_hub_download

    from norefund.core import secrets

    notes = None
    if repo_id.startswith(_GATED_HF_PREFIXES):
        notes = "Gated repo — requires a HuggingFace account/token to download."

    try:
        resolved = hf_hub_download(
            repo_id=repo_id,
            filename="tokenizer.json",
            local_files_only=True,
            token=secrets.get_hf_token(),
        )
        cache_path = Path(resolved)
        size = cache_path.stat().st_size
        return TokenizerResource(
            key=f"hf:{repo_id}",
            backend="hf",
            name=repo_id,
            model_ids=(),
            is_cached=True,
            cache_path=cache_path,
            size_bytes=size,
            source_url=f"https://huggingface.co/{repo_id}",
            notes=notes,
        )
    except OSError:
        return TokenizerResource(
            key=f"hf:{repo_id}",
            backend="hf",
            name=repo_id,
            model_ids=(),
            is_cached=False,
            cache_path=None,
            size_bytes=None,
            source_url=f"https://huggingface.co/{repo_id}",
            notes=notes,
        )


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------


def _download_tiktoken(
    resource: TokenizerResource,
    *,
    on_progress: ProgressFn | None,
    cancel_event,
) -> TokenizerResource:
    import urllib.request

    if resource.source_url is None:
        raise ResourceDownloadError(f"No source URL known for '{resource.name}'.")

    _blob_url, expected_hash = _capture_tiktoken_blob(resource.name)
    cache_dir = paths.tiktoken_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha1(resource.source_url.encode()).hexdigest()
    cache_path = cache_dir / cache_key
    tmp_path = cache_dir / f"{cache_key}.download"

    try:
        with urllib.request.urlopen(resource.source_url) as response:
            total = response.length
            downloaded = 0
            hasher = hashlib.sha256()
            with open(tmp_path, "wb") as fh:
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise DownloadCancelled()
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
                    hasher.update(chunk)
                    downloaded += len(chunk)
                    if on_progress is not None:
                        on_progress(downloaded, total)

        if expected_hash and hasher.hexdigest() != expected_hash:
            raise ResourceDownloadError(
                f"Downloaded file for '{resource.name}' failed hash verification."
            )

        os.replace(tmp_path, cache_path)
    except DownloadCancelled:
        tmp_path.unlink(missing_ok=True)
        raise
    except ResourceDownloadError:
        tmp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise ResourceDownloadError(
            f"Failed to download tokenizer '{resource.name}': {exc}"
        ) from exc

    return probe_tiktoken(resource.name)


def _download_hf(
    resource: TokenizerResource,
    *,
    on_progress: ProgressFn | None,
    cancel_event,
) -> TokenizerResource:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

    from norefund.core import secrets

    if on_progress is not None:
        on_progress(0, None)
    try:
        hf_hub_download(
            repo_id=resource.name,
            filename="tokenizer.json",
            token=secrets.get_hf_token(),
        )
    except GatedRepoError as exc:
        raise ResourceDownloadError(
            f"'{resource.name}' is a gated repo — request access at "
            f"https://huggingface.co/{resource.name} and try again."
        ) from exc
    except HfHubHTTPError as exc:
        raise ResourceDownloadError(
            f"Failed to download '{resource.name}': {exc}"
        ) from exc
    except Exception as exc:
        raise ResourceDownloadError(
            f"Failed to download '{resource.name}': {exc}"
        ) from exc
    if on_progress is not None:
        on_progress(1, 1)

    return probe_hf(resource.name)


def download_tokenizer(
    resource: TokenizerResource,
    *,
    on_progress: ProgressFn | None = None,
    cancel_event=None,
) -> TokenizerResource:
    if resource.backend == "tiktoken":
        result = _download_tiktoken(
            resource, on_progress=on_progress, cancel_event=cancel_event
        )
    else:
        result = _download_hf(
            resource, on_progress=on_progress, cancel_event=cancel_event
        )

    from norefund.core.tokenization import invalidate_tokenizer_cache

    invalidate_tokenizer_cache()
    return result
