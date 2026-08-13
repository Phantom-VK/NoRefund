r"""Settings persistence — loads/saves user preferences to a per-user JSON file.

Storage location (platform-appropriate):
  - Linux:   ~/.config/NoRefund/settings.json
  - macOS:   ~/Library/Application Support/NoRefund/settings.json
  - Windows: C:\Users\<user>\AppData\Local\PhantomVK\NoRefund\settings.json
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from platformdirs import user_config_dir

from norefund.logging_config import get_logger

_LOG = get_logger(__name__)

Theme = Literal["system", "light", "dark"]

_DEFAULTS: dict = {
    "default_output_tokens": 1024,
    "theme": "system",
    "currency": "USD",
    "show_chunk_warnings": True,
    "onboarding_dismissed": False,
}


@dataclass
class Settings:
    default_output_tokens: int = 1024
    theme: Theme = "system"
    currency: str = "USD"
    show_chunk_warnings: bool = True
    onboarding_dismissed: bool = False


class SettingsStore:
    """Reads and writes Settings to a local JSON config file."""

    def __init__(self) -> None:
        cfg_dir = Path(
            user_config_dir(appname="NoRefund", appauthor="PhantomVK", ensure_exists=True)  # noqa: E501
        )
        self._path = cfg_dir / "settings.json"
        _LOG.info("settings_store_init", extra={"ctx": {"path": str(self._path)}})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> Settings:
        """Return persisted settings, or defaults if file absent/corrupt."""
        if not self._path.exists():
            _LOG.info("settings_not_found_using_defaults")
            return Settings()

        try:
            data: dict = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _LOG.warning(
                "settings_load_failed",
                extra={"ctx": {"error": str(exc)}},
            )
            return Settings()

        return Settings(
            default_output_tokens=int(
                data.get("default_output_tokens", _DEFAULTS["default_output_tokens"])
            ),
            theme=data.get("theme", _DEFAULTS["theme"]),  # type: ignore[arg-type]
            currency=data.get("currency", _DEFAULTS["currency"]),
            show_chunk_warnings=bool(
                data.get("show_chunk_warnings", _DEFAULTS["show_chunk_warnings"])
            ),
            onboarding_dismissed=bool(
                data.get("onboarding_dismissed", _DEFAULTS["onboarding_dismissed"])
            ),
        )

    def save(self, settings: Settings) -> None:
        """Persist settings to disk. Silently logs on write failure."""
        try:
            self._path.write_text(
                json.dumps(asdict(settings), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            _LOG.info("settings_saved", extra={"ctx": {"path": str(self._path)}})
        except OSError as exc:
            _LOG.warning(
                "settings_save_failed",
                extra={"ctx": {"error": str(exc)}},
            )

    @property
    def path(self) -> Path:
        """Expose config file path (useful for Settings modal 'Open folder' button)."""
        return self._path
