"""The js_api bridge: dialogs, settings, and the dataclass<->TS contract.

No pywebview window is created — `Api._window` is stubbed with a fake
exposing just `create_file_dialog`/`run_js`, matching how the real
`webview.Window` is used.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

from norefund.core.architectures import ModelArchitecture
from norefund.core.compare import ModelComparison
from norefund.core.currency import ExchangeRates
from norefund.core.hardware_registry import HardwareTarget
from norefund.core.models_registry import ModelInfo, list_models
from norefund.core.portfolio import PortfolioProjection
from norefund.core.resources import ManagedDir, ResourceReport, TokenizerResource
from norefund.core.selfhost import FitResult, MemoryEstimate
from norefund.core.service import AnalysisResult
from norefund.core.settings import Settings
from norefund.desktop.api import Api

_TYPES_TS = (
    Path(__file__).resolve().parents[1] / "frontend" / "src" / "lib" / "types.ts"
)


class _FakeWindow:
    def __init__(self, dialog_result=None):
        self.dialog_result = dialog_result
        self.calls: list[tuple] = []

    def create_file_dialog(self, dialog_type, **kwargs):
        self.calls.append((dialog_type, kwargs))
        return self.dialog_result

    def run_js(self, script: str) -> None:
        pass


def test_get_app_version_returns_a_nonempty_string():
    api = Api()
    out = api.get_app_version()
    assert out["ok"] is True
    assert isinstance(out["data"], str)
    assert out["data"]


def test_get_models_returns_all_models_with_full_fields():
    api = Api()
    out = api.get_models()
    assert out["ok"] is True
    models = out["data"]
    assert len(models) == len(list_models())
    expected_fields = {f.name for f in dataclasses.fields(ModelInfo)}
    for m in models:
        assert set(m.keys()) == expected_fields


def test_get_settings_roundtrips_through_save_settings(tmp_path):
    api = Api()
    api._settings_store._path = tmp_path / "settings.json"
    original = api.get_settings()["data"]
    saved = api.save_settings(original)["data"]
    assert saved == original


def test_evaluate_fit_unknown_architecture_returns_ok_false():
    api = Api()
    out = api.evaluate_fit("nope", "nope-hw", "q4_k_m", 8192, "fp16")
    assert out["ok"] is False
    assert "error" in out


def test_get_exchange_rates_returns_cached_or_fallback(tmp_path, monkeypatch):
    import norefund.core.currency as currency_module

    monkeypatch.setattr(
        currency_module, "_cache_path", lambda: tmp_path / "exchange_rates.json"
    )
    api = Api()
    out = api.get_exchange_rates()
    assert out["ok"] is True
    assert out["data"]["base"] == "USD"
    assert "EUR" in out["data"]["rates"]


def test_refresh_exchange_rates_wraps_fetch_failure_as_ok_false(monkeypatch):
    import urllib.error

    def raise_error(req, timeout=None):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    api = Api()
    out = api.refresh_exchange_rates()
    assert out["ok"] is False
    assert "error" in out


def test_save_file_appends_missing_extension():
    api = Api()
    api._window = _FakeWindow(dialog_result=("/tmp/report",))
    out = api.save_file("report", "pdf", "PDF report")
    assert out["ok"] is True
    assert out["data"] == "/tmp/report.pdf"


def test_save_file_leaves_present_extension_alone():
    api = Api()
    api._window = _FakeWindow(dialog_result=("/tmp/report.pdf",))
    out = api.save_file("report", "pdf", "PDF report")
    assert out["data"] == "/tmp/report.pdf"


def test_save_file_returns_none_when_dialog_is_cancelled():
    api = Api()
    api._window = _FakeWindow(dialog_result=None)
    out = api.save_file("report", "pdf", "PDF report")
    assert out["ok"] is True
    assert out["data"] is None


def test_pick_files_filters_to_supported_extensions():
    api = Api()
    api._window = _FakeWindow(dialog_result=("/tmp/a.pdf",))
    out = api.pick_files()
    assert out["ok"] is True
    assert out["data"] == ["/tmp/a.pdf"]
    dialog_type, kwargs = api._window.calls[0]
    assert kwargs["allow_multiple"] is True
    (pattern,) = kwargs["file_types"]
    assert "*.pdf" in pattern
    assert "*.docx" in pattern


def test_pick_files_returns_empty_list_when_dialog_is_cancelled():
    api = Api()
    api._window = _FakeWindow(dialog_result=None)
    out = api.pick_files()
    assert out["ok"] is True
    assert out["data"] == []


def test_get_logs_returns_empty_list_when_no_log_file_exists(monkeypatch):
    monkeypatch.setattr("norefund.desktop.api.latest_log_file", lambda: None)
    api = Api()
    out = api.get_logs()
    assert out["ok"] is True
    assert out["data"] == []


def test_get_logs_parses_json_lines_and_survives_malformed_ones(tmp_path, monkeypatch):
    log_path = tmp_path / "norefund-test.log"
    log_path.write_text(
        '{"level": "INFO", "message": "hello", "ctx": {"k": "v"}}\n'
        "not json\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("norefund.desktop.api.latest_log_file", lambda: log_path)
    api = Api()
    out = api.get_logs()
    assert out["ok"] is True
    assert out["data"] == [
        {"level": "INFO", "message": "hello", "ctx": {"k": "v"}},
        {"level": "INFO", "message": "not json", "ctx": {}},
    ]


def test_get_logs_respects_limit(tmp_path, monkeypatch):
    log_path = tmp_path / "norefund-test.log"
    lines = [f'{{"level": "INFO", "message": "line{i}"}}' for i in range(10)]
    log_path.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setattr("norefund.desktop.api.latest_log_file", lambda: log_path)
    api = Api()
    out = api.get_logs(limit=3)
    assert [e["message"] for e in out["data"]] == ["line7", "line8", "line9"]


# -- dataclass <-> TS interface contract --------------------------------


def _ts_interface_fields(name: str) -> set[str]:
    text = _TYPES_TS.read_text(encoding="utf-8")
    match = re.search(rf"interface {name} \{{(.*?)\n\}}", text, re.S)
    assert match, f"interface {name} not found in {_TYPES_TS}"
    fields = set()
    for line in match.group(1).splitlines():
        line = line.strip()
        field_match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\??:", line)
        if field_match:
            fields.add(field_match.group(1))
    return fields


_CONTRACT_CLASSES = [
    ModelInfo,
    AnalysisResult,
    ModelComparison,
    PortfolioProjection,
    FitResult,
    MemoryEstimate,
    TokenizerResource,
    ManagedDir,
    ResourceReport,
    Settings,
    ModelArchitecture,
    HardwareTarget,
    ExchangeRates,
]


@pytest.mark.parametrize("cls", _CONTRACT_CLASSES, ids=lambda c: c.__name__)
def test_dataclass_fields_match_ts_interface(cls):
    py_fields = {f.name for f in dataclasses.fields(cls)}
    ts_fields = _ts_interface_fields(cls.__name__)
    assert py_fields == ts_fields, (
        f"{cls.__name__}: python has {py_fields - ts_fields or '{}'}, "
        f"ts has {ts_fields - py_fields or '{}'}"
    )
