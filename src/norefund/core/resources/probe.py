"""Cache-status probing for tiktoken and HuggingFace tokenizers.

Read-only: never downloads or writes to the cache. tiktoken probing uses a
"capture, don't load" trick (patch `read_file_cached` to intercept the blob
URL) so checking cache status never parses/decodes real vocab data.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from norefund.core import paths
from norefund.core.models_registry import ModelInfo, list_models
from norefund.core.resources.types import TokenizerResource

_LOG = logging.getLogger(__name__)

_GATED_HF_PREFIXES = ("meta-llama/", "google/gemma-")


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


def probe_hf(repo_id: str) -> TokenizerResource:
    from huggingface_hub import hf_hub_download

    from norefund.core import secrets

    notes = None
    if repo_id.startswith(_GATED_HF_PREFIXES):
        notes = "Gated repo. Set your HuggingFace token in the app's Settings to download this."  # noqa: E501

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
