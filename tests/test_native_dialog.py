"""Tests for native_dialog.py's zenity polling and extension-append logic."""

from __future__ import annotations

import norefund.gui.native_dialog as native_dialog


class _FakeProcess:
    """Minimal Popen stand-in: `poll_sequence` is popped once per poll()
    call (None while "running", an exit code once "finished"), matching
    real Popen semantics closely enough to drive _run_zenity's loop."""

    def __init__(self, poll_sequence, stdout="", stderr="", returncode=0):
        self._poll_sequence = list(poll_sequence)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def poll(self):
        return self._poll_sequence.pop(0) if self._poll_sequence else self.returncode

    def communicate(self):
        return self.stdout, self.stderr


def _patch_zenity_process(monkeypatch, process: _FakeProcess) -> None:
    monkeypatch.setattr(native_dialog.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(native_dialog.tk, "_default_root", None)
    monkeypatch.setattr(native_dialog.time, "sleep", lambda _s: None)


def test_run_zenity_polls_until_process_exits_and_returns_completed_process(
    monkeypatch,
):
    process = _FakeProcess(poll_sequence=[None, None, 0], stdout="chosen.txt\n")
    _patch_zenity_process(monkeypatch, process)

    result = native_dialog._run_zenity(["zenity", "--file-selection"])

    assert result.returncode == 0
    assert result.stdout == "chosen.txt\n"
    assert process._poll_sequence == []  # polled exactly 3 times, exhausting it


def test_ask_save_file_appends_missing_extension_on_zenity_path(monkeypatch):
    monkeypatch.setattr(native_dialog, "_zenity_available", lambda: True)
    _patch_zenity_process(
        monkeypatch, _FakeProcess(poll_sequence=[0], stdout="report\n")
    )

    result = native_dialog.ask_save_file(
        defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
    )

    assert result == "report.pdf"


def test_ask_save_file_keeps_existing_extension_on_zenity_path(monkeypatch):
    monkeypatch.setattr(native_dialog, "_zenity_available", lambda: True)
    _patch_zenity_process(
        monkeypatch, _FakeProcess(poll_sequence=[0], stdout="report.pdf\n")
    )

    result = native_dialog.ask_save_file(
        defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
    )

    assert result == "report.pdf"


def test_ask_save_file_returns_empty_string_on_cancel(monkeypatch):
    monkeypatch.setattr(native_dialog, "_zenity_available", lambda: True)
    _patch_zenity_process(
        monkeypatch,
        _FakeProcess(poll_sequence=[native_dialog._USER_CANCELLED], returncode=1),
    )

    result = native_dialog.ask_save_file(
        defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
    )

    assert result == ""
