from __future__ import annotations

from norefund.core import paths


def test_bundled_resource_dev_mode_resolves_to_existing_file():
    resolved = paths.bundled_resource("config/default_models.yaml")
    assert resolved.exists()


def test_bundled_resource_frozen_mode_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    resolved = paths.bundled_resource("config/default_models.yaml")
    assert resolved == tmp_path / "norefund" / "config" / "default_models.yaml"


def test_tiktoken_cache_dir_respects_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("TIKTOKEN_CACHE_DIR", str(tmp_path))
    assert paths.tiktoken_cache_dir() == tmp_path


def test_tiktoken_cache_dir_defaults_under_app_data_dir(monkeypatch):
    monkeypatch.delenv("TIKTOKEN_CACHE_DIR", raising=False)
    resolved = paths.tiktoken_cache_dir()
    assert resolved.parent == paths.app_data_dir()
    assert resolved.name == "tiktoken-cache"


def test_app_config_dir_and_app_log_dir_are_distinct():
    assert paths.app_config_dir() != paths.app_log_dir()
