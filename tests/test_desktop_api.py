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

_TEST_MODEL = ModelInfo(
    id="test:model",
    display_name="Test Model",
    provider="Test",
    tokenizer_backend="tiktoken",
    tokenizer_name="cl100k_base",
    context_window=1000,
    input_price_per_million=1.0,
    output_price_per_million=2.0,
)

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


def test_export_analysis_writes_a_real_file_at_the_returned_path(tmp_path):
    api = Api()
    dest = tmp_path / "analysis.csv"
    api._window = _FakeWindow(dialog_result=(str(dest),))
    result = AnalysisResult(
        file_path="a.txt",
        model_id="test:model",
        char_count=10,
        word_count=2,
        token_count=5,
        context_window=1000,
        context_usage_pct=0.5,
        fits_in_context=True,
        min_chunks_needed=1,
        estimated_input_cost=0.001,
        error=None,
    )
    out = api.export_analysis([dataclasses.asdict(result)], "csv")
    # The bug this guards: save_file is @_guard-wrapped, so a naive
    # self.save_file(...) call from export_analysis would hand back an
    # {"ok", "data"} envelope instead of a path, and Path(envelope) would
    # blow up -- caught by export_analysis's own @_guard and reported as
    # ok: False instead of ever writing anything.
    assert out["ok"] is True
    assert out["data"] == str(dest)
    assert dest.exists()
    assert "a.txt" in dest.read_text(encoding="utf-8")


def test_export_analysis_returns_none_when_dialog_is_cancelled():
    api = Api()
    api._window = _FakeWindow(dialog_result=None)
    out = api.export_analysis([], "csv")
    assert out["ok"] is True
    assert out["data"] is None


def test_export_comparison_writes_a_real_file_at_the_returned_path(tmp_path):
    api = Api()
    dest = tmp_path / "comparison.csv"
    api._window = _FakeWindow(dialog_result=(str(dest),))
    comparison = ModelComparison(
        model=_TEST_MODEL,
        token_count=100,
        context_usage_pct=10.0,
        fits_in_context=True,
        min_chunks_needed=1,
        output_tokens=50,
        input_cost=0.0001,
        output_cost=0.0001,
        total_cost=0.0002,
        tokenizer_is_approximate=False,
        error=None,
    )
    report = {
        "source_label": "test",
        "results": [
            {**dataclasses.asdict(comparison), "model": dataclasses.asdict(_TEST_MODEL)}
        ],
    }
    out = api.export_comparison(report, None, None, "csv")
    assert out["ok"] is True
    assert out["data"] == str(dest)
    assert dest.exists()
    assert "Test Model" in dest.read_text(encoding="utf-8")


def test_export_fit_writes_a_real_file_at_the_returned_path(tmp_path):
    api = Api()
    dest = tmp_path / "fit-check.html"
    api._window = _FakeWindow(dialog_result=(str(dest),))
    estimate = MemoryEstimate(
        weights_bytes=500_000,
        kv_cache_bytes_per_sequence=1_000,
        kv_cache_bytes=1_000,
        activation_bytes=1_000,
        framework_overhead_bytes=1_000,
        total_bytes=503_000,
    )
    fit = FitResult(
        architecture_id="test-arch",
        hardware_id="test-hw",
        quantization="fp16",
        kv_cache_dtype="fp16",
        context_length=4096,
        concurrency=1,
        usable_memory_bytes=1_000_000,
        estimate=estimate,
        fits=True,
        headroom_bytes=100,
        utilization_pct=10.0,
        max_concurrent_requests=1,
    )
    out = api.export_fit(dataclasses.asdict(fit), {}, "html")
    assert out["ok"] is True
    assert out["data"] == str(dest)
    assert dest.exists()


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
