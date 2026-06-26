"""Tokenizer backends. Each backend counts tokens for a given model."""

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
    """NOTE: First use downloads the tokenizer from HuggingFace Hub (~few MB)."""

    def __init__(self, model_name: str) -> None:
        from tokenizers import Tokenizer

        _LOG.info(
            "hf_tokenizer_loading",
            extra={"ctx": {"model": model_name}},
        )
        try:
            self._tokenizer = Tokenizer.from_pretrained(model_name)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load HuggingFace tokenizer '{model_name}'. "
                f"Check internet connection for first-time downloads. Error: {exc}"
            ) from exc

    def count(self, text: str) -> int:
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
