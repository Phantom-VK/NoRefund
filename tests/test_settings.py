from __future__ import annotations

import json

from norefund.core.settings import Settings, SettingsStore


def test_default_settings_has_show_chunk_warnings_true() -> None:
    assert Settings().show_chunk_warnings is True


def test_settings_store_roundtrip_show_chunk_warnings(tmp_path) -> None:
    store = SettingsStore()
    store._path = tmp_path / "settings.json"

    store.save(Settings(show_chunk_warnings=False))
    loaded = store.load()

    assert loaded.show_chunk_warnings is False


def test_default_settings_has_onboarding_dismissed_false() -> None:
    assert Settings().onboarding_dismissed is False


def test_settings_store_roundtrip_onboarding_dismissed(tmp_path) -> None:
    store = SettingsStore()
    store._path = tmp_path / "settings.json"

    store.save(Settings(onboarding_dismissed=True))
    loaded = store.load()

    assert loaded.onboarding_dismissed is True


def test_settings_load_missing_field_defaults_true(tmp_path) -> None:
    store = SettingsStore()
    store._path = tmp_path / "settings.json"
    store._path.write_text(
        json.dumps({"default_output_tokens": 2048, "theme": "dark", "currency": "EUR"}),
        encoding="utf-8",
    )

    loaded = store.load()

    assert loaded.show_chunk_warnings is True
    assert loaded.default_output_tokens == 2048
