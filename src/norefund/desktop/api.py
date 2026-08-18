"""The js_api bridge: one method per use case, reachable from the frontend as
`window.pywebview.api.<name>`.

Every public method is wrapped with `@_guard` so an exception inside `core`
surfaces to JS as a structured `{ok: False, error}` instead of an opaque
rejection. `lib/bridge.ts` unwraps this envelope, so views never see it.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

import webview

from norefund.core import currency, secrets
from norefund.core.architectures import get_architecture as core_get_architecture
from norefund.core.architectures import list_architectures
from norefund.core.compare import (
    CompareReport,
    ModelComparison,
    compare_paths,
    compare_text,
)
from norefund.core.compare import what_if as core_what_if
from norefund.core.export import (
    analysis_results_to_csv,
    analysis_results_to_markdown,
    comparison_to_csv,
    comparison_to_markdown,
)
from norefund.core.hardware_registry import get_hardware as core_get_hardware
from norefund.core.hardware_registry import list_hardware
from norefund.core.models_registry import ModelInfo, list_models
from norefund.core.portfolio import PortfolioProjection, cheapest_that_fits
from norefund.core.portfolio import project_costs as core_project_costs
from norefund.core.quantization import (
    kv_cache_dtype_display_name,
    list_kv_cache_dtypes,
    list_quantization_levels,
    quantization_display_name,
)
from norefund.core.report.html import render_html
from norefund.core.report.model import ReportModel
from norefund.core.report.pdf import render_pdf
from norefund.core.resources import (
    DownloadCancelled,
    TokenizerResource,
    build_resource_report,
)
from norefund.core.resources import download_tokenizer as core_download_tokenizer
from norefund.core.selfhost import FitResult, MemoryEstimate
from norefund.core.selfhost import evaluate_fit as core_evaluate_fit
from norefund.core.service import AnalysisResult, analyze_file, analyze_folder
from norefund.core.settings import Settings, SettingsStore
from norefund.desktop.dto import to_jsonable
from norefund.desktop.jobs import JobEvent, JobManager

logger = logging.getLogger(__name__)

_FALLBACK_VERSION = "0.1.0"


def _guard(fn):
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return {"ok": True, "data": fn(self, *args, **kwargs)}
        except Exception as exc:  # noqa: BLE001
            logger.exception("api.%s failed", fn.__name__)
            return {"ok": False, "error": str(exc)}

    return wrapper


# -- dict -> dataclass reconstruction ------------------------------------
# Mirrors of dto.to_jsonable, for the payloads the frontend sends back
# (export_*, what_if). Field names match exactly — see dto.py's docstring.


def _model_info(d: dict) -> ModelInfo:
    return ModelInfo(**d)


def _analysis_result(d: dict) -> AnalysisResult:
    return AnalysisResult(**d)


def _model_comparison(d: dict) -> ModelComparison:
    d = dict(d)
    d["model"] = _model_info(d["model"])
    return ModelComparison(**d)


def _compare_report(d: dict) -> CompareReport:
    return CompareReport(
        source_label=d["source_label"],
        results=[_model_comparison(r) for r in d["results"]],
    )


def _memory_estimate(d: dict | None) -> MemoryEstimate | None:
    return MemoryEstimate(**d) if d is not None else None


def _fit_result(d: dict) -> FitResult:
    d = dict(d)
    d["estimate"] = _memory_estimate(d.get("estimate"))
    d["warnings"] = tuple(d.get("warnings", ()))
    return FitResult(**d)


def _portfolio_projection(d: dict) -> PortfolioProjection:
    d = dict(d)
    d["model"] = _model_info(d["model"])
    return PortfolioProjection(**d)


class Api:
    def __init__(self) -> None:
        self._window: webview.Window | None = None
        self._jobs: JobManager | None = None
        self._settings_store = SettingsStore()

    # -- lifecycle --------------------------------------------------------

    def bind_window(self, window: webview.Window) -> None:
        self._window = window
        self._jobs = JobManager(emit=self._push)

    def _push(self, event: JobEvent) -> None:
        detail = json.dumps(
            {"job_id": event.job_id, "kind": event.kind, "payload": event.payload}
        )
        # run_js, not evaluate_js: we do not need a return value, and run_js
        # does not block the worker thread waiting for the UI thread to answer.
        assert self._window is not None
        self._window.run_js(
            f"window.dispatchEvent(new CustomEvent('norefund:job',"
            f"{{detail:{detail}}}))"
        )

    def _models_by_id(self, model_ids: list[str]) -> list[ModelInfo]:
        catalog = {m.id: m for m in list_models()}
        try:
            return [catalog[mid] for mid in model_ids]
        except KeyError as exc:
            raise ValueError(f"Unknown model id: {exc.args[0]}") from exc

    # -- app metadata -------------------------------------------------------

    @_guard
    def get_app_version(self) -> str:
        try:
            return pkg_version("norefund")
        except PackageNotFoundError:
            return _FALLBACK_VERSION

    # -- registry / static data --------------------------------------------

    @_guard
    def get_models(self) -> list[dict]:
        return to_jsonable(list_models())

    @_guard
    def get_architectures(self) -> list[dict]:
        return to_jsonable(list_architectures())

    @_guard
    def get_hardware(self) -> list[dict]:
        return to_jsonable(list_hardware())

    @_guard
    def get_quantization_levels(self) -> list[dict]:
        return [
            {"value": q, "label": quantization_display_name(q)}
            for q in list_quantization_levels()
        ]

    @_guard
    def get_kv_cache_dtypes(self) -> list[dict]:
        return [
            {"value": d, "label": kv_cache_dtype_display_name(d)}
            for d in list_kv_cache_dtypes()
        ]

    # -- settings & secrets --------------------------------------------------

    @_guard
    def get_settings(self) -> dict:
        return to_jsonable(self._settings_store.load())

    @_guard
    def save_settings(self, settings: dict) -> dict:
        parsed = Settings(**settings)
        self._settings_store.save(parsed)
        return to_jsonable(parsed)

    @_guard
    def keyring_available(self) -> bool:
        return secrets.keyring_available()

    @_guard
    def has_hf_token(self) -> bool:
        return secrets.get_hf_token() is not None

    @_guard
    def set_hf_token(self, token: str) -> None:
        secrets.set_hf_token(token)

    @_guard
    def delete_hf_token(self) -> None:
        secrets.delete_hf_token()

    # -- currency -------------------------------------------------------------

    @_guard
    def get_exchange_rates(self) -> dict:
        """Cached rates only -- no network. Callers get whatever was last
        fetched (or the built-in fallback), instantly."""
        return to_jsonable(currency.load_cached_rates())

    @_guard
    def refresh_exchange_rates(self) -> dict:
        """The one place the frontend can trigger currency.py's network
        call -- wired to an explicit "Refresh rates" action in Settings,
        never automatic."""
        return to_jsonable(currency.fetch_exchange_rates())

    # -- native dialogs (replaces gui/native_dialog.py entirely) ------------

    @_guard
    def pick_files(self) -> list[str]:
        assert self._window is not None
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True
        )
        return list(result) if result else []

    @_guard
    def pick_folder(self) -> str | None:
        assert self._window is not None
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not result:
            return None
        return result if isinstance(result, str) else result[0]

    @_guard
    def save_file(self, suggested_name: str, extension: str, label: str) -> str | None:
        assert self._window is not None
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=suggested_name,
            file_types=(f"{label} (*.{extension})",),
        )
        if not result:
            return None
        path = result if isinstance(result, str) else result[0]
        # The extension is not guaranteed to be applied by every platform's
        # native dialog, so enforce it here rather than per call site.
        if not path.lower().endswith(f".{extension}"):
            path = f"{path}.{extension}"
        return path

    # -- jobs -----------------------------------------------------------------

    @_guard
    def start_analysis(self, paths: list[str], model_id: str) -> str:
        targets = [Path(p) for p in paths]
        assert self._jobs is not None

        def work(cancel, report):
            results: list[AnalysisResult] = []
            for target in targets:
                if cancel.is_set():
                    break
                if target.is_dir():
                    results.extend(
                        analyze_folder(
                            target, model_id, on_progress=report, cancel_event=cancel
                        )
                    )
                else:
                    result = analyze_file(target, model_id)
                    results.append(result)
                    report(result)
            return results

        return self._jobs.start(work)

    @_guard
    def start_compare(
        self, text: str, paths: list[str], model_ids: list[str], output_tokens: int
    ) -> str:
        models = self._models_by_id(model_ids)
        targets = [Path(p) for p in paths]
        assert self._jobs is not None

        def work(cancel, report):
            if targets:
                return compare_paths(
                    targets,
                    models,
                    output_tokens,
                    on_progress=lambda p: report(str(p)),
                    cancel_event=cancel,
                )
            return compare_text(text, models, output_tokens)

        return self._jobs.start(work)

    @_guard
    def start_resource_scan(self) -> str:
        assert self._jobs is not None

        def work(cancel, report):
            return build_resource_report()

        return self._jobs.start(work)

    @_guard
    def start_download(self, resource_key: str) -> str:
        snapshot = build_resource_report()
        resource: TokenizerResource | None = next(
            (r for r in snapshot.tokenizers if r.key == resource_key), None
        )
        if resource is None:
            raise ValueError(f"Unknown tokenizer resource '{resource_key}'")
        assert self._jobs is not None

        def work(cancel, report):
            try:
                return core_download_tokenizer(
                    resource,
                    on_progress=lambda done, total: report(
                        {"downloaded": done, "total": total}
                    ),
                    cancel_event=cancel,
                )
            except DownloadCancelled:
                # core signals cancellation by raising; JobManager's protocol
                # (Task 2) signals it via KeyboardInterrupt — translate here
                # rather than changing either contract.
                raise KeyboardInterrupt from None

        return self._jobs.start(work)

    @_guard
    def cancel_job(self, job_id: str) -> bool:
        assert self._jobs is not None
        return self._jobs.cancel(job_id)

    # -- synchronous compute ----------------------------------------------

    @_guard
    def evaluate_fit(
        self,
        architecture_id: str,
        hardware_id: str,
        quantization: str,
        context_length: int,
        kv_cache_dtype: str,
        concurrency: int = 1,
    ) -> dict:
        # get_* (not find_*) so an unknown id raises and this call comes back
        # as {"ok": False, ...} instead of a FitResult with an error field.
        architecture = core_get_architecture(architecture_id)
        hardware = core_get_hardware(hardware_id)
        result = core_evaluate_fit(
            architecture,
            hardware,
            quantization,
            context_length,
            concurrency=concurrency,
            kv_cache_dtype=kv_cache_dtype,
        )
        return to_jsonable(result)

    @_guard
    def project_costs(
        self,
        corpus_tokens: dict[str, int],
        output_tokens: int,
        runs_per_period: float,
        frequency: str,
        model_ids: list[str],
    ) -> dict:
        models = self._models_by_id(model_ids)
        projections = core_project_costs(
            corpus_tokens, output_tokens, runs_per_period, frequency, models
        )
        cheapest = cheapest_that_fits(projections)
        return to_jsonable({"projections": projections, "cheapest": cheapest})

    @_guard
    def what_if(self, report: dict, output_tokens: int) -> dict:
        comparison = _model_comparison(report)
        result = core_what_if(comparison, output_tokens, comparison.model)
        return to_jsonable(result)

    # -- export -----------------------------------------------------------

    @_guard
    def export_analysis(self, results: list[dict], fmt: str) -> str | None:
        path = self.save_file("analysis", fmt, "Analysis report")
        if path is None:
            return None
        analysis = [_analysis_result(r) for r in results]
        self._write_export(
            path, fmt, analysis=analysis, title="NoRefund Analysis Report"
        )
        return path

    @_guard
    def export_comparison(
        self,
        report: dict,
        projections: list[dict] | None,
        frequency_label: str | None,
        fmt: str,
    ) -> str | None:
        path = self.save_file("comparison", fmt, "Comparison report")
        if path is None:
            return None
        compare_report = _compare_report(report)
        portfolio = (
            [_portfolio_projection(p) for p in projections] if projections else None
        )
        if fmt in ("csv", "md"):
            text = (
                comparison_to_csv(compare_report)
                if fmt == "csv"
                else comparison_to_markdown(compare_report)
            )
            Path(path).write_text(text, encoding="utf-8")
        else:
            self._write_export(
                path,
                fmt,
                comparison=compare_report,
                portfolio=portfolio,
                portfolio_frequency_label=frequency_label,
                title="NoRefund Comparison Report",
            )
        return path

    @_guard
    def export_fit(self, fit: dict, names: dict, fmt: str) -> str | None:
        path = self.save_file("fit-check", fmt, "Fit check report")
        if path is None:
            return None
        self._write_export(
            path,
            fmt,
            fit=_fit_result(fit),
            fit_architecture_name=names.get("architecture"),
            fit_hardware_name=names.get("hardware"),
            fit_quantization_name=names.get("quantization"),
            fit_kv_cache_name=names.get("kv_cache"),
            title="NoRefund Fit Check Report",
        )
        return path

    def _write_export(
        self, path: str, fmt: str, *, title: str, **report_fields: Any
    ) -> None:
        if fmt == "csv" and "analysis" in report_fields:
            Path(path).write_text(
                analysis_results_to_csv(report_fields["analysis"]), encoding="utf-8"
            )
            return
        if fmt == "md" and "analysis" in report_fields:
            Path(path).write_text(
                analysis_results_to_markdown(report_fields["analysis"]),
                encoding="utf-8",
            )
            return
        report = ReportModel(title=title, generated_at=datetime.now(), **report_fields)
        if fmt == "pdf":
            Path(path).write_bytes(render_pdf(report))
        elif fmt == "html":
            Path(path).write_text(render_html(report), encoding="utf-8")
        else:
            raise ValueError(f"Unknown export format: {fmt}")

    @_guard
    def open_path(self, path: str) -> bool:
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
            return True
        except Exception:  # noqa: BLE001
            return False

    @_guard
    def open_url(self, url: str) -> bool:
        return webbrowser.open(url)
