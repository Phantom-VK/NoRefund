"""Tokenizer downloads — the only place in `core/` that performs network I/O,
and only ever called on explicit user action from the GUI's Resources view.
"""

from __future__ import annotations

import hashlib
import os

from norefund.core import paths
from norefund.core.resources.types import (
    DownloadCancelled,
    ProgressFn,
    ResourceDownloadError,
    TokenizerResource,
)


def _download_tiktoken(
    resource: TokenizerResource,
    *,
    on_progress: ProgressFn | None,
    cancel_event,
) -> TokenizerResource:
    import urllib.request

    # Deferred + resolved via the package namespace (not a direct import of
    # norefund.core.resources.probe) so that tests monkeypatching
    # `norefund.core.resources._capture_tiktoken_blob`/`probe_tiktoken` on the
    # package object still take effect here.
    from norefund.core import resources as _resources

    if resource.source_url is None:
        raise ResourceDownloadError(f"No source URL known for '{resource.name}'.")

    _blob_url, expected_hash = _resources._capture_tiktoken_blob(resource.name)
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

    return _resources.probe_tiktoken(resource.name)


def _download_hf(
    resource: TokenizerResource,
    *,
    on_progress: ProgressFn | None,
    cancel_event,
) -> TokenizerResource:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.errors import GatedRepoError, HfHubHTTPError

    from norefund.core import resources as _resources
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

    return _resources.probe_hf(resource.name)


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
