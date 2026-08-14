from __future__ import annotations

from pathlib import Path

from norefund.core import paths

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "src" / "norefund" / "config"
_SPEC_FILE = _PROJECT_ROOT / "packaging" / "norefund.spec"


def test_bundled_resource_dev_mode_resolves_to_existing_file():
    resolved = paths.bundled_resource("config/default_models.yaml")
    assert resolved.exists()


def test_model_architectures_yaml_resolves_to_existing_file():
    resolved = paths.bundled_resource("config/model_architectures.yaml")
    assert resolved.exists()


def test_hardware_yaml_resolves_to_existing_file():
    resolved = paths.bundled_resource("config/hardware.yaml")
    assert resolved.exists()


def test_every_config_yaml_is_listed_in_the_packaging_spec():
    # bundled_resource() only finds files at runtime if PyInstaller's spec
    # was told to bundle them -- a config/ file present here but missing
    # from the spec's `datas` list works in dev and silently breaks the
    # frozen build with a FileNotFoundError.
    spec_text = _SPEC_FILE.read_text()
    for yaml_file in _CONFIG_DIR.glob("*.yaml"):
        assert yaml_file.name in spec_text, (
            f"{yaml_file.name} is not listed in packaging/norefund.spec's datas"
        )


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
