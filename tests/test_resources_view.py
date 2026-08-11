"""Smoke tests for ResourcesView's scan/download/cancel/error flows.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import pytest

ctk = pytest.importorskip("customtkinter")

import norefund.gui.resources_view as resources_view_module  # noqa: E402
from norefund.core.resources import (  # noqa: E402
    DownloadCancelled,
    ManagedDir,
    ResourceDownloadError,
    ResourceReport,
    TokenizerResource,
)
from norefund.gui import formatting  # noqa: E402
from norefund.gui.resources_view import ResourcesView, _TokenizerRow  # noqa: E402

from .conftest import _pump, _pump_until  # noqa: E402


@dataclass
class _FakeShell:
    models: list


def _make_resource(
    key="tiktoken:o200k_base", *, cached=False, notes=None
) -> TokenizerResource:
    return TokenizerResource(
        key=key,
        backend="tiktoken",
        name="o200k_base",
        model_ids=("openai:gpt-4o",),
        is_cached=cached,
        cache_path=Path("/fake/cache/o200k_base") if cached else None,
        size_bytes=1024 if cached else None,
        source_url="https://example.invalid/o200k_base.tiktoken",
        notes=notes,
    )


def _make_report(*resources: TokenizerResource) -> ResourceReport:
    total = sum(r.size_bytes or 0 for r in resources)
    return ResourceReport(
        tokenizers=list(resources),
        dirs=[
            ManagedDir(
                label="Config",
                path=Path("/fake/config"),
                exists=True,
                size_bytes=42,
                file_count=1,
            )
        ],
        total_tokenizer_bytes=total,
    )


def _action_buttons(row: _TokenizerRow) -> list[ctk.CTkButton]:
    return [
        w for w in row._action_area.winfo_children() if isinstance(w, ctk.CTkButton)
    ]


def _patch_scan(monkeypatch, result) -> None:
    """Point ResourcesView's scan at a fake build_resource_report.

    `result` may be a ResourceReport (returned as-is) or any callable
    taking `models` (used directly), so slow/blocking fakes work too.
    """
    fn = result if callable(result) else (lambda models: result)
    monkeypatch.setattr(resources_view_module, "build_resource_report", fn)


def test_scan_renders_rows_and_stat_pills(root, monkeypatch):
    report = _make_report(
        _make_resource(cached=True),
        _make_resource(key="tiktoken:cl100k_base"),
    )
    _patch_scan(monkeypatch, report)

    view = ResourcesView(root, _FakeShell(models=[]))
    _pump_until(root, lambda: not view._loading)

    assert set(view._rows) == {r.key for r in report.tokenizers}
    assert view._downloaded_pill._value_label.cget("text") == "1 of 2"
    assert view._size_pill._value_label.cget("text") == formatting.fmt_bytes(
        report.total_tokenizer_bytes
    )


def test_download_progress_flips_row_to_cached_and_updates_pills(root, monkeypatch):
    resource = _make_resource(cached=False)
    report = _make_report(resource)
    _patch_scan(monkeypatch, report)

    progress_calls: list[tuple[int, int | None]] = []

    def fake_download(res, *, on_progress=None, cancel_event=None):
        if on_progress is not None:
            on_progress(512, 1024)
            progress_calls.append((512, 1024))
        return _make_resource(key=res.key, cached=True)

    monkeypatch.setattr(resources_view_module, "download_tokenizer", fake_download)

    view = ResourcesView(root, _FakeShell(models=[]))
    _pump_until(root, lambda: not view._loading)

    view.start_download(view._report.tokenizers[0])
    _pump_until(root, lambda: not view.is_busy())

    assert progress_calls
    row = view._rows[resource.key]
    buttons = _action_buttons(row)
    assert any("Open folder" in b.cget("text") for b in buttons)
    assert view._downloaded_pill._value_label.cget("text") == "1 of 1"


def test_cancel_resets_row_to_download_state(root, monkeypatch):
    resource = _make_resource(cached=False)
    report = _make_report(resource)
    _patch_scan(monkeypatch, report)

    def fake_download(res, *, on_progress=None, cancel_event=None):
        raise DownloadCancelled()

    monkeypatch.setattr(resources_view_module, "download_tokenizer", fake_download)

    view = ResourcesView(root, _FakeShell(models=[]))
    _pump_until(root, lambda: not view._loading)

    view.start_download(view._report.tokenizers[0])
    _pump_until(root, lambda: not view.is_busy())

    row = view._rows[resource.key]
    labels = [b.cget("text") for b in _action_buttons(row)]
    assert any("Download" in text for text in labels)
    assert not any("Cancel" in text for text in labels)


def test_download_error_renders_inline(root, monkeypatch):
    resource = _make_resource(cached=False)
    report = _make_report(resource)
    _patch_scan(monkeypatch, report)

    def fake_download(res, *, on_progress=None, cancel_event=None):
        raise ResourceDownloadError("network unreachable")

    monkeypatch.setattr(resources_view_module, "download_tokenizer", fake_download)

    view = ResourcesView(root, _FakeShell(models=[]))
    _pump_until(root, lambda: not view._loading)

    view.start_download(view._report.tokenizers[0])
    _pump_until(root, lambda: not view.is_busy())

    row = view._rows[resource.key]
    assert row._error_label.cget("text") == "network unreachable"
    assert row._error_label.grid_info() != {}


def test_gated_repo_note_shows_open_page_link(root, monkeypatch):
    _patch_scan(monkeypatch, _make_report())
    view = ResourcesView(root, _FakeShell(models=[]))
    _pump_until(root, lambda: not view._loading)

    gated = TokenizerResource(
        key="hf:meta-llama/Meta-Llama-3-8B",
        backend="hf",
        name="Meta-Llama-3-8B",
        model_ids=("meta:llama-3-8b",),
        is_cached=False,
        cache_path=None,
        size_bytes=None,
        source_url="https://huggingface.co/meta-llama/Meta-Llama-3-8B",
        notes="Gated repo — requires HF account/token",
    )
    row = _TokenizerRow(view._scroll, gated, view)
    assert row._error_label.cget("text").endswith("open page")
    assert row._error_label.cget("cursor") == "hand2"


def test_destroy_mid_scan_does_not_crash(root, monkeypatch):
    proceed = threading.Event()

    def slow_report(models):
        proceed.wait(2)
        return _make_report()

    _patch_scan(monkeypatch, slow_report)
    view = ResourcesView(root, _FakeShell(models=[]))
    assert view._loading is True
    view.destroy()
    proceed.set()
    _pump(root, 300)
