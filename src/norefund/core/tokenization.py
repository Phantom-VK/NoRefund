"""Tokenizer backends. Each backend counts tokens for a given model."""

from __future__ import annotations

import logging
import re
from typing import Protocol

from norefund.core.models_registry import ModelInfo

_LOG = logging.getLogger(__name__)
_tokenizer_cache: dict[str, "TokenizerBackend"] = {}


class TokenizerBackend(Protocol):
    def count(self, text: str) -> int: ...


class TikTokenBackend:
    def __init__(self, model_name: str) -> None:
        import tiktoken

        self._enc = None
        try:
            self._enc = tiktoken.encoding_for_model(model_name)
        except KeyError:
            try:
                self._enc = tiktoken.get_encoding("cl100k_base")
                _LOG.warning(
                    "tiktoken_model_not_found",
                    extra={"ctx": {"model": model_name, "fallback": "cl100k_base"}},
                )
            except Exception as exc:
                _LOG.warning(
                    "tiktoken_unavailable",
                    extra={"ctx": {"model": model_name, "error": str(exc)}},
                )
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

    OFFLINE-FIRST: Only loads from the local HuggingFace cache. If the
    tokenizer files are not already cached, a clear RuntimeError is raised
    instead of silently downloading from the internet.

    To cache a tokenizer for offline use, run once with internet access:

        python -c "from tokenizers import Tokenizer; Tokenizer.from_pretrained('<model>')"

    The files will be stored under the default HF cache directory
    (~/.cache/huggingface/hub on Linux/macOS).
    """

    def __init__(self, model_name: str) -> None:
        from tokenizers import Tokenizer

        _LOG.info(
            "hf_tokenizer_loading",
            extra={"ctx": {"model": model_name}},
        )
        try:
            self._tokenizer = Tokenizer.from_pretrained(
                model_name,
                # Prevent any network call — only use locally cached files.
                # Raises EnvironmentError / OSError if files are not cached.
                local_files_only=True,
            )
        except (OSError, EnvironmentError) as exc:
            raise RuntimeError(
                f"HuggingFace tokenizer '{model_name}' is not available in the local cache.\n"
                "To download it once (requires internet access), run:\n"
                f"  python -c \"from tokenizers import Tokenizer; "
                f"Tokenizer.from_pretrained('{model_name}')\"\n"
                "After that, NoRefund will use it fully offline."
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load HuggingFace tokenizer '{model_name}': {exc}"
            ) from exc

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._tokenizer.encode(text).ids)


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
