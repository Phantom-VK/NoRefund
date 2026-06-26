"""Tokenizer backends. Each backend counts tokens for a given model."""

import logging
import re
from typing import Protocol

from norefund.core.models_registry import ModelInfo

_LOG = logging.getLogger(__name__)


class TokenizerBackend(Protocol):
    def count(self, text: str) -> int: ...


class TikTokenBackend:
    """Backend for OpenAI and compatible models using tiktoken."""

    def __init__(self, model_name: str) -> None:
        import tiktoken

        self._enc = None
        self._using_fallback = False

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
                self._enc = None
                self._using_fallback = True
                _LOG.warning(
                    "tiktoken_unavailable",
                    extra={"ctx": {"model": model_name, "error": str(exc)}},
                )
        except Exception as exc:
            self._enc = None
            self._using_fallback = True
            _LOG.warning(
                "tiktoken_unavailable",
                extra={"ctx": {"model": model_name, "error": str(exc)}},
            )

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._enc is not None:
            return len(self._enc.encode(text))
        # Regex approximation — counts are inaccurate. User was warned at init.
        _LOG.warning(
            "token_count_approximate",
            extra={"ctx": {"reason": "tiktoken unavailable, using regex word-split approximation"}},
        )
        return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


class HFTokenizerBackend:
    """Backend for HuggingFace models using the lightweight tokenizers library.

    NOTE: First use of a model downloads the tokenizer from HuggingFace Hub
    (~a few MB). Subsequent runs use the local cache.
    """

    def __init__(self, model_name: str) -> None:
        from tokenizers import Tokenizer

        _LOG.info(
            "hf_tokenizer_loading",
            extra={"ctx": {"model": model_name, "note": "may download from HuggingFace Hub on first use"}},
        )
        try:
            self._tokenizer = Tokenizer.from_pretrained(model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load HuggingFace tokenizer '{model_name}'. "
                f"Check your internet connection for first-time downloads. Error: {exc}"
            ) from exc

    def count(self, text: str) -> int:
        return len(self._tokenizer.encode(text).ids)


def get_tokenizer(model: ModelInfo) -> TokenizerBackend:
    """Factory: return the right backend for the given model."""
    if model.tokenizer_backend == "tiktoken":
        return TikTokenBackend(model.tokenizer_name)
    if model.tokenizer_backend == "hf":
        return HFTokenizerBackend(model.tokenizer_name)
    raise ValueError(f"Unknown tokenizer backend: '{model.tokenizer_backend}'")
