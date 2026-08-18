"""USD -> display-currency conversion for cost figures.

Every model price in the registry is USD-denominated (models_registry.ModelInfo
defaults currency="USD"), so conversion always runs FROM USD TO the user's
chosen display currency.

fetch_exchange_rates() is the only network call in this module. Like
core/resources.download_tokenizer, it must only ever be invoked on explicit
user action (the Settings view's "Refresh rates" button) -- never
automatically -- so the app's "network only when you explicitly ask" promise
holds. Switching the display currency itself is a pure, local recompute
against whatever rates are already cached; no network call.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from norefund.core import paths

SUPPORTED_CURRENCIES: tuple[str, ...] = ("USD", "EUR", "GBP", "INR")

# Approximate fallback rates (USD -> currency), used before the first
# successful fetch, or if a fetch ever fails. Always superseded by a real
# fetch once the user asks for one via fetch_exchange_rates().
_FALLBACK_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.0,
}

# api.frankfurter.dev: free, no API key, ECB-sourced. The older
# api.frankfurter.app domain redirects here and gets blocked without a
# User-Agent header, so this module talks to .dev directly.
_API_URL = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR,GBP,INR"
_REQUEST_TIMEOUT = 10
_CACHE_FILENAME = "exchange_rates.json"


@dataclass(frozen=True)
class ExchangeRates:
    base: str
    rates: dict[str, float]
    # ISO 8601 UTC timestamp of the last successful fetch; None for the
    # built-in fallback, so callers/UI can distinguish "never fetched" from
    # "fetched a while ago."
    fetched_at: str | None


class CurrencyFetchError(RuntimeError):
    """Raised when fetch_exchange_rates() can't reach or parse the API."""


def _cache_path() -> Path:
    return paths.app_data_dir() / _CACHE_FILENAME


def fallback_rates() -> ExchangeRates:
    return ExchangeRates(base="USD", rates=dict(_FALLBACK_RATES), fetched_at=None)


def load_cached_rates() -> ExchangeRates:
    """Never raises -- falls back to the built-in constants if nothing has
    been fetched yet or the cache file is unreadable/corrupt."""
    path = _cache_path()
    if not path.exists():
        return fallback_rates()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExchangeRates(
            base=data["base"],
            rates={k: float(v) for k, v in data["rates"].items()},
            fetched_at=data.get("fetched_at"),
        )
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
        return fallback_rates()


def save_rates(rates: ExchangeRates) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(rates), indent=2), encoding="utf-8")


def fetch_exchange_rates() -> ExchangeRates:
    """Fetch fresh USD exchange rates and persist them to the local cache.

    The one network call in this module -- only ever called from explicit
    user action, matching core/resources.download_tokenizer's contract.
    """
    request = urllib.request.Request(_API_URL, headers={"User-Agent": "NoRefund/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise CurrencyFetchError(
            f"Could not reach the exchange-rate service: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CurrencyFetchError(
            "Exchange-rate service returned an unexpected response."
        ) from exc

    try:
        rates = {"USD": 1.0, **{k: float(v) for k, v in payload["rates"].items()}}
    except (KeyError, TypeError, ValueError) as exc:
        raise CurrencyFetchError(
            "Exchange-rate service returned an unexpected response."
        ) from exc

    result = ExchangeRates(
        base="USD", rates=rates, fetched_at=datetime.now(UTC).isoformat()
    )
    save_rates(result)
    return result


def convert(amount_usd: float, to_currency: str, rates: ExchangeRates) -> float:
    """Convert a USD amount into to_currency using the given rates.

    An unknown currency (e.g. a stale cache missing one added later) falls
    through unconverted (rate 1.0) rather than raising, so the UI never
    crashes over a currency it doesn't have a rate for yet.
    """
    rate = rates.rates.get(to_currency, 1.0)
    return amount_usd * rate
