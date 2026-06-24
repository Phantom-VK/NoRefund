"""Tokenizer backends. Each backend counts tokens for a given model."""

from typing import Protocol

from norefund.core.models_registry import ModelInfo


class TokenizerBackend(Protocol):
    def count(self, text: str) -> int: ...


class TikTokenBackend:
    """Backend for OpenAI and compatible models using tiktoken."""

    def __init__(self, model_name: str) -> None:
        import tiktoken

        # Falls back to cl100k_base if model name not found in tiktoken registry
        try:
            self._enc = tiktoken.encoding_for_model(model_name)
        except KeyError:
            self._enc = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        return len(self._enc.encode(text))


class HFTokenizerBackend:
    """Backend for HuggingFace models using the lightweight tokenizers library."""

    def __init__(self, model_name: str) -> None:
        from tokenizers import Tokenizer

        self._tokenizer = Tokenizer.from_pretrained(model_name)

    def count(self, text: str) -> int:
        # .encode() returns an Encoding object; .ids is the list of token integers
        return len(self._tokenizer.encode(text).ids)


def get_tokenizer(model: ModelInfo) -> TokenizerBackend:
    """Factory: return the right backend for the given model."""
    if model.tokenizer_backend == "tiktoken":
        return TikTokenBackend(model.tokenizer_name)
    if model.tokenizer_backend == "hf":
        return HFTokenizerBackend(model.tokenizer_name)
    raise ValueError(f"Unknown tokenizer backend: {model.tokenizer_backend}")
