from __future__ import annotations

import hashlib
import io
import threading

import pytest

from norefund.core import resources
from norefund.core.models_registry import ModelInfo


def _model(backend: str, tokenizer_name: str, model_id: str = "test:model") -> ModelInfo:
    return ModelInfo(
        id=model_id,
        display_name="Test",
        provider="Test",
        tokenizer_backend=backend,
        tokenizer_name=tokenizer_name,
        context_window=1000,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
    )


# ---------------------------------------------------------------------------
# Enumeration / dedupe
# ---------------------------------------------------------------------------


def test_required_tokenizers_canonicalizes_tiktoken_model_names():
    models = [_model("tiktoken", "gpt-4o", "a"), _model("tiktoken", "gpt-4o-mini", "b")]
    rows = resources.required_tokenizers(models)
    assert {name for _, name, _ in rows} == {"o200k_base"}


def test_required_tokenizers_keeps_already_canonical_encoding_names():
    rows = resources.required_tokenizers([_model("tiktoken", "cl100k_base", "a")])
    assert rows == [("tiktoken", "cl100k_base", "a")]


def test_group_by_resource_dedupes_and_collects_model_ids():
    models = [
        _model("tiktoken", "gpt-4o", "openai:gpt-4o"),
        _model("tiktoken", "gpt-4o-mini", "openai:gpt-4o-mini"),
        _model("hf", "deepseek-ai/DeepSeek-V3", "deepseek:v3"),
    ]
    grouped = resources._group_by_resource(models)
    assert grouped[("tiktoken", "o200k_base")] == ["openai:gpt-4o", "openai:gpt-4o-mini"]
    assert grouped[("hf", "deepseek-ai/DeepSeek-V3")] == ["deepseek:v3"]


# ---------------------------------------------------------------------------
# tiktoken probe
# ---------------------------------------------------------------------------


def test_probe_tiktoken_capture_matches_tiktoken_internals():
    """Canary: fails loudly if tiktoken's internal API used for probing changes."""
    blob_url, expected_hash = resources._capture_tiktoken_blob("cl100k_base")
    assert blob_url.startswith("https://")
    assert expected_hash is not None


def test_probe_tiktoken_reports_miss_when_not_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    result = resources.probe_tiktoken("cl100k_base")
    assert result.is_cached is False
    assert result.cache_path is None
    assert result.source_url is not None


def test_probe_tiktoken_reports_hit_after_planting_cache_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    blob_url, _ = resources._capture_tiktoken_blob("cl100k_base")
    cache_key = hashlib.sha1(blob_url.encode()).hexdigest()
    planted = tmp_path / cache_key
    planted.write_bytes(b"fake-vocab-data")

    result = resources.probe_tiktoken("cl100k_base")

    assert result.is_cached is True
    assert result.size_bytes == len(b"fake-vocab-data")
    assert result.cache_path == planted


# ---------------------------------------------------------------------------
# HF probe
# ---------------------------------------------------------------------------


def test_probe_hf_reports_miss_when_not_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    result = resources.probe_hf("deepseek-ai/DeepSeek-V3")
    assert result.is_cached is False
    assert result.cache_path is None


def test_probe_hf_reports_hit_when_cached(tmp_path, monkeypatch):
    fixture = tmp_path / "tokenizer.json"
    fixture.write_bytes(b"1234567890")
    monkeypatch.setattr(
        "huggingface_hub.hf_hub_download", lambda **kwargs: str(fixture)
    )
    result = resources.probe_hf("fake/repo")
    assert result.is_cached is True
    assert result.size_bytes == 10


def test_probe_hf_flags_gated_repos():
    result = resources.probe_hf("meta-llama/Meta-Llama-3-8B")
    assert result.notes is not None
    assert "gated" in result.notes.lower()


def test_probe_hf_passes_stored_token(tmp_path, monkeypatch):
    fixture = tmp_path / "tokenizer.json"
    fixture.write_bytes(b"1234567890")
    captured = {}

    def fake_download(**kwargs):
        captured.update(kwargs)
        return str(fixture)

    monkeypatch.setattr("huggingface_hub.hf_hub_download", fake_download)
    monkeypatch.setattr(
        "norefund.core.secrets.get_hf_token", lambda: "hf_secrettoken"
    )
    resources.probe_hf("fake/repo")
    assert captured["token"] == "hf_secrettoken"


def test_download_hf_passes_stored_token(monkeypatch):
    captured = {}

    def fake_download(**kwargs):
        captured.update(kwargs)
        return "irrelevant"

    monkeypatch.setattr("huggingface_hub.hf_hub_download", fake_download)
    monkeypatch.setattr(
        "norefund.core.secrets.get_hf_token", lambda: "hf_secrettoken"
    )
    monkeypatch.setattr(
        resources, "probe_hf", lambda name: object()
    )
    monkeypatch.setattr(
        "norefund.core.tokenization.invalidate_tokenizer_cache", lambda: None
    )
    resource = resources.TokenizerResource(
        key="hf:fake/repo",
        backend="hf",
        name="fake/repo",
        model_ids=(),
        is_cached=False,
        cache_path=None,
        size_bytes=None,
        source_url="https://huggingface.co/fake/repo",
    )
    resources.download_tokenizer(resource)
    assert captured["token"] == "hf_secrettoken"


# ---------------------------------------------------------------------------
# dir_stats
# ---------------------------------------------------------------------------


def test_dir_stats_counts_files_and_bytes(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"12345")
    (tmp_path / "b.txt").write_bytes(b"1234567890")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_bytes(b"123")

    total, count = resources.dir_stats(tmp_path)

    assert total == 5 + 10 + 3
    assert count == 3


def test_dir_stats_missing_dir_returns_zero():
    from pathlib import Path

    assert resources.dir_stats(Path("/nonexistent-xyz")) == (0, 0)


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._buf = io.BytesIO(data)
        self.length = len(data)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size: int) -> bytes:
        return self._buf.read(size)


def test_download_tiktoken_happy_path_writes_cache_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    blob_url, expected_hash = resources._capture_tiktoken_blob("cl100k_base")
    data = b"vocab-bytes"

    resource = resources.TokenizerResource(
        key="tiktoken:cl100k_base",
        backend="tiktoken",
        name="cl100k_base",
        model_ids=(),
        is_cached=False,
        cache_path=None,
        size_bytes=None,
        source_url=blob_url,
    )

    monkeypatch.setattr(
        "norefund.core.resources._capture_tiktoken_blob",
        lambda name: (blob_url, hashlib.sha256(data).hexdigest()),
    )
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda url: _FakeResponse(data)
    )
    monkeypatch.setattr(
        "norefund.core.tokenization.invalidate_tokenizer_cache", lambda: None
    )

    result = resources.download_tokenizer(resource)

    cache_key = hashlib.sha1(blob_url.encode()).hexdigest()
    assert (tmp_path / cache_key).read_bytes() == data
    assert result.is_cached is True


def test_download_tiktoken_hash_mismatch_raises_and_cleans_up(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    blob_url = "https://example.com/fake.tiktoken"
    data = b"vocab-bytes"

    resource = resources.TokenizerResource(
        key="tiktoken:cl100k_base",
        backend="tiktoken",
        name="cl100k_base",
        model_ids=(),
        is_cached=False,
        cache_path=None,
        size_bytes=None,
        source_url=blob_url,
    )

    monkeypatch.setattr(
        "norefund.core.resources._capture_tiktoken_blob",
        lambda name: (blob_url, "0" * 64),
    )
    monkeypatch.setattr("urllib.request.urlopen", lambda url: _FakeResponse(data))

    with pytest.raises(resources.ResourceDownloadError):
        resources.download_tokenizer(resource)

    cache_key = hashlib.sha1(blob_url.encode()).hexdigest()
    assert not (tmp_path / cache_key).exists()
    assert not (tmp_path / f"{cache_key}.download").exists()


def test_download_tiktoken_cancel_mid_stream_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    blob_url = "https://example.com/fake.tiktoken"
    data = b"x" * 200_000

    resource = resources.TokenizerResource(
        key="tiktoken:cl100k_base",
        backend="tiktoken",
        name="cl100k_base",
        model_ids=(),
        is_cached=False,
        cache_path=None,
        size_bytes=None,
        source_url=blob_url,
    )

    monkeypatch.setattr(
        "norefund.core.resources._capture_tiktoken_blob",
        lambda name: (blob_url, hashlib.sha256(data).hexdigest()),
    )
    monkeypatch.setattr("urllib.request.urlopen", lambda url: _FakeResponse(data))

    cancel_event = threading.Event()
    cancel_event.set()

    with pytest.raises(resources.DownloadCancelled):
        resources.download_tokenizer(resource, cancel_event=cancel_event)

    cache_key = hashlib.sha1(blob_url.encode()).hexdigest()
    assert not (tmp_path / cache_key).exists()
