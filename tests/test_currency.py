from __future__ import annotations

import io
import json

import pytest

from norefund.core import currency


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._buf = io.BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)


def test_fallback_rates_covers_every_supported_currency():
    rates = currency.fallback_rates()
    assert rates.fetched_at is None
    assert set(currency.SUPPORTED_CURRENCIES) <= set(rates.rates)


def test_load_cached_rates_falls_back_when_nothing_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(currency, "_cache_path", lambda: tmp_path / "missing.json")
    rates = currency.load_cached_rates()
    assert rates == currency.fallback_rates()


def test_save_and_load_rates_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(
        currency, "_cache_path", lambda: tmp_path / "exchange_rates.json"
    )
    saved = currency.ExchangeRates(
        base="USD",
        rates={"EUR": 0.9, "GBP": 0.8, "INR": 83.0},
        fetched_at="2026-01-01T00:00:00+00:00",
    )
    currency.save_rates(saved)
    loaded = currency.load_cached_rates()
    assert loaded == saved


def test_load_cached_rates_falls_back_on_corrupt_cache(tmp_path, monkeypatch):
    path = tmp_path / "exchange_rates.json"
    path.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(currency, "_cache_path", lambda: path)
    assert currency.load_cached_rates() == currency.fallback_rates()


def test_convert_usd_to_usd_is_identity():
    rates = currency.fallback_rates()
    assert currency.convert(10.0, "USD", rates) == 10.0


def test_convert_applies_rate():
    rates = currency.ExchangeRates(base="USD", rates={"EUR": 0.5}, fetched_at=None)
    assert currency.convert(10.0, "EUR", rates) == 5.0


def test_convert_unknown_currency_falls_through_unconverted():
    rates = currency.ExchangeRates(base="USD", rates={"EUR": 0.5}, fetched_at=None)
    assert currency.convert(10.0, "JPY", rates) == 10.0


def test_fetch_exchange_rates_happy_path_saves_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        currency, "_cache_path", lambda: tmp_path / "exchange_rates.json"
    )
    payload = json.dumps(
        {
            "amount": 1.0,
            "base": "USD",
            "date": "2026-01-01",
            "rates": {"EUR": 0.9, "GBP": 0.8, "INR": 83.0},
        }
    ).encode("utf-8")
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda req, timeout=None: _FakeResponse(payload)
    )

    result = currency.fetch_exchange_rates()

    assert result.rates["USD"] == 1.0
    assert result.rates["EUR"] == 0.9
    assert result.fetched_at is not None
    assert currency.load_cached_rates() == result


def test_fetch_exchange_rates_wraps_network_error(monkeypatch):
    import urllib.error

    def raise_error(req, timeout=None):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr("urllib.request.urlopen", raise_error)

    with pytest.raises(currency.CurrencyFetchError):
        currency.fetch_exchange_rates()


def test_fetch_exchange_rates_wraps_malformed_payload(monkeypatch):
    payload = json.dumps({"unexpected": "shape"}).encode("utf-8")
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda req, timeout=None: _FakeResponse(payload)
    )

    with pytest.raises(currency.CurrencyFetchError):
        currency.fetch_exchange_rates()
