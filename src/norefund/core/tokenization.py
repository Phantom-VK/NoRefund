"""Tokenizer backends. Each backend counts tokens for a given model."""

from typing import Protocol

from norefund.core.models_registry import ModelInfo


class TokenizerBackend(Protocol):
    def count(self, text: str) -> int: ...


class TikTokenBackend:
    """Backend for OpenAI and compatible models using tiktoken."""

    def __init__(self, model_name: str) -> None:
        import tiktoken

        self._enc = tiktoken.encoding_for_model(model_name)

    def count(self, text: str) -> int:
        return len(self._enc.encode(text))


class TransformersBackend:
    """Backend for HuggingFace models using AutoTokenizer."""

    def __init__(self, model_name: str) -> None:
        from tokenizers import Tokenizer

        self._tokenizer = Tokenizer.from_pretrained(model_name)

    def count(self, text: str) -> int:
        return len(self._tokenizer.encode(text))


def get_tokenizer(model: ModelInfo) -> TokenizerBackend:
    """Factory: return the right backend for the given model."""
    if model.tokenizer_backend == "tiktoken":
        return TikTokenBackend(model.tokenizer_name)
    if model.tokenizer_backend == "transformers":
        return TransformersBackend(model.tokenizer_name)
    raise ValueError(f"Unknown tokenizer backend: {model.tokenizer_backend}")
