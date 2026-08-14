"""Tokenizer backends. Each backend counts tokens for a given model."""

from __future__ import annotations

import logging
import re
from typing import Protocol

from norefund.core.models_registry import ModelInfo

_LOG = logging.getLogger(__name__)
_tokenizer_cache: dict[str, TokenizerBackend] = {}


class TokenizerBackend(Protocol):
    def count(self, text: str) -> int: ...


class TikTokenOfflineError(RuntimeError):
    """Raised when a tiktoken encoding isn't cached locally.

    tiktoken silently downloads encoding vocab files from the internet on
    first use. NoRefund only ever goes to the network on explicit user
    action (the Resources view's Download button), so this error is
    raised instead of letting that implicit network call happen.
    """


class _TikTokenNetworkBlocked(Exception):
    """Internal signal: tiktoken attempted to fetch data over the network."""


def _blocked_read_file(blobpath: str) -> bytes:
    raise _TikTokenNetworkBlocked(blobpath)


def _load_tiktoken_local_only(loader):
    """Run a tiktoken loader while blocking any network fetch it may attempt.

    Raises _TikTokenNetworkBlocked instead of downloading when the requested
    encoding is not already present in the local tiktoken cache.
    """
    import tiktoken.load as tiktoken_load

    original_read_file = tiktoken_load.read_file
    tiktoken_load.read_file = _blocked_read_file
    try:
        return loader()
    finally:
        tiktoken_load.read_file = original_read_file


def _offline_cache_hint(encoding_or_model: str) -> str:
    return (
        f"tiktoken encoding for '{encoding_or_model}' is not downloaded yet.\n"
        "Open the Resources view in NoRefund to download it (one click).\n"
        "Or, from the CLI:\n"
        "  python -c \"import tiktoken; "
        f"tiktoken.get_encoding('{encoding_or_model}')\""
    )


class TikTokenBackend:
    def __init__(self, model_name: str) -> None:
        import tiktoken

        self._enc = None
        try:
            self._enc = _load_tiktoken_local_only(
                lambda: tiktoken.encoding_for_model(model_name)
            )
        except KeyError:
            try:
                self._enc = _load_tiktoken_local_only(
                    lambda: tiktoken.get_encoding("cl100k_base")
                )
                _LOG.warning(
                    "tiktoken_model_not_found",
                    extra={"ctx": {"model": model_name, "fallback": "cl100k_base"}},
                )
            except _TikTokenNetworkBlocked as exc:
                raise TikTokenOfflineError(_offline_cache_hint("cl100k_base")) from exc
            except Exception as exc:
                _LOG.warning(
                    "tiktoken_unavailable",
                    extra={"ctx": {"model": model_name, "error": str(exc)}},
                )
        except _TikTokenNetworkBlocked as exc:
            raise TikTokenOfflineError(_offline_cache_hint(model_name)) from exc
        except Exception as exc:
            _LOG.warning(
                "tiktoken_unavailable",
                extra={"ctx": {"model": model_name, "error": str(exc)}},
            )

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._enc is not None:
            return len(self._enc.encode(text))
        _LOG.warning("token_count_approximate")
        return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


class HFTokenizerBackend:
    """HuggingFace tokenizer backend.

    Only loads from the local HuggingFace cache. If the tokenizer files
    are not already cached, a clear RuntimeError is raised instead of
    silently downloading from the internet — downloads only happen via
    the Resources view's Download button (`core/resources.download_tokenizer`).

    The files are stored under the default HF cache directory
    (~/.cache/huggingface/hub on Linux/macOS).
    """

    def __init__(self, model_name: str) -> None:
        # NOTE: tokenizers.Tokenizer.from_pretrained() does not accept
        # local_files_only, so it cannot enforce local-only loading itself.
        # huggingface_hub.hf_hub_download() does, so we resolve the cached
        # file path through it and hand that straight to Tokenizer.from_file.
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        _LOG.info(
            "hf_tokenizer_loading",
            extra={"ctx": {"model": model_name}},
        )
        try:
            tokenizer_path = hf_hub_download(
                repo_id=model_name,
                filename="tokenizer.json",
                local_files_only=True,
            )
            self._tokenizer = Tokenizer.from_file(tokenizer_path)
        except OSError as exc:
            raise RuntimeError(
                f"HuggingFace tokenizer '{model_name}' is not downloaded yet.\n"
                "Open the Resources view in NoRefund to download it (one click).\n"
                "Or, from the CLI:\n"
                "  python -c \"from huggingface_hub import hf_hub_download; "
                f"hf_hub_download('{model_name}', 'tokenizer.json')\""
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load HuggingFace tokenizer '{model_name}': {exc}"
            ) from exc

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._tokenizer.encode(text).ids)


def invalidate_tokenizer_cache() -> None:
    """Drop all memoized tokenizer backends.

    Called after a successful download so a backend that fell back to
    approximate counting (or raised) picks up the newly cached files on
    its next use, without requiring an app restart.
    """
    _tokenizer_cache.clear()


def get_tokenizer(model: ModelInfo) -> TokenizerBackend:
    if model.id in _tokenizer_cache:
        return _tokenizer_cache[model.id]
    if model.tokenizer_backend == "tiktoken":
        backend: TokenizerBackend = TikTokenBackend(model.tokenizer_name)
    elif model.tokenizer_backend == "hf":
        backend = HFTokenizerBackend(model.tokenizer_name)
    else:
        raise ValueError(f"Unknown tokenizer backend: '{model.tokenizer_backend}'")
    _tokenizer_cache[model.id] = backend
    return backend
