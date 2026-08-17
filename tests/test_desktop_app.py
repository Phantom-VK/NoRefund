"""Entrypoint resolution and runtime checks for the desktop shell.

No window is created here — pywebview needs a real display. These cover the
pure decision logic that would otherwise only fail at launch time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from norefund.desktop import app as desktop_app


def test_dev_entrypoint_used_when_env_var_set(monkeypatch):
    monkeypatch.setenv("NOREFUND_DEV", "1")
    assert desktop_app.resolve_entrypoint() == desktop_app.DEV_SERVER_URL


def test_built_entrypoint_used_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("NOREFUND_DEV", raising=False)
    index = tmp_path / "index.html"
    index.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(desktop_app, "WEB_DIR", tmp_path)
    assert desktop_app.resolve_entrypoint() == index


def test_missing_build_raises_actionable_error(monkeypatch, tmp_path):
    monkeypatch.delenv("NOREFUND_DEV", raising=False)
    monkeypatch.setattr(desktop_app, "WEB_DIR", tmp_path / "nope")
    with pytest.raises(RuntimeError, match="npm run build"):
        desktop_app.resolve_entrypoint()


def test_preferred_gui_is_platform_appropriate(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert desktop_app.preferred_gui() == "gtk"
    monkeypatch.setattr(sys, "platform", "win32")
    assert desktop_app.preferred_gui() == "edgechromium"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert desktop_app.preferred_gui() is None


def test_window_size_is_clamped_to_small_screens():
    # 1366x768 is still a very common Windows laptop panel; the Tk build's
    # minsize(1180, 760) made the app impossible to fit on one.
    w, h = desktop_app.initial_window_size(1366, 768)
    assert w <= 1366 and h <= 768 - 40


def test_window_size_uses_preferred_on_large_screens():
    w, h = desktop_app.initial_window_size(2560, 1440)
    assert (w, h) == (1440, 900)


def test_missing_runtime_message_is_none_when_backend_importable(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert desktop_app.missing_runtime_message() is None
