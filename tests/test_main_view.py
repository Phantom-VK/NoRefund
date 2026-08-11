"""Smoke tests for MainView: view registration, first-run banner, shortcuts.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import threading

import pytest

ctk = pytest.importorskip("customtkinter")

import norefund.core.resources as resources_module  # noqa: E402
import norefund.gui.main_view as main_view_module  # noqa: E402
import norefund.gui.resources_view as resources_view_module  # noqa: E402
from norefund.core.resources import ResourceReport, TokenizerResource  # noqa: E402
from norefund.core.settings import Settings  # noqa: E402
from norefund.gui.main_view import MainView  # noqa: E402

from .conftest import _pump, _pump_until  # noqa: E402


class _FakeSettingsStore:
    def __init__(self, initial: Settings) -> None:
        self._settings = initial
        self.saved: list[Settings] = []

    def load(self) -> Settings:
        return self._settings

    def save(self, settings: Settings) -> None:
        self.saved.append(settings)
        self._settings = settings


def _empty_report() -> ResourceReport:
    return ResourceReport(tokenizers=[], dirs=[], total_tokenizer_bytes=0)


def _cached_report() -> ResourceReport:
    resource = TokenizerResource(
        key="tiktoken:o200k_base",
        backend="tiktoken",
        name="o200k_base",
        model_ids=("openai:gpt-4o",),
        is_cached=True,
        cache_path=None,
        size_bytes=1024,
        source_url=None,
    )
    return ResourceReport(tokenizers=[resource], dirs=[], total_tokenizer_bytes=1024)


def _build_main_view(
    root, monkeypatch, *, onboarding_dismissed: bool = True, report=None
) -> MainView:
    store = _FakeSettingsStore(Settings(onboarding_dismissed=onboarding_dismissed))
    monkeypatch.setattr(main_view_module, "SettingsStore", lambda: store)
    report = report or _cached_report()
    # Patched in both places: MainView's onboarding check re-imports this
    # name from core.resources at call time, but ResourcesView (built when
    # show_view navigates there) bound its own copy at module-import time.
    def fake_scan(models):
        return report

    monkeypatch.setattr(resources_module, "build_resource_report", fake_scan)
    monkeypatch.setattr(resources_view_module, "build_resource_report", fake_scan)
    view = MainView(root)
    view.pack(fill="both", expand=True)
    return view


def test_show_view_builds_all_five_views_without_raising(root, monkeypatch):
    view = _build_main_view(root, monkeypatch)
    for view_id in (
        MainView.VIEW_CALCULATOR,
        MainView.VIEW_PARSER,
        MainView.VIEW_REGISTRY,
        MainView.VIEW_RESOURCES,
        MainView.VIEW_COMPARE,
    ):
        view.show_view(view_id)
        _pump(root, 30)
        assert view._current_view == view_id
        assert view_id in view._view_cache


def test_first_run_banner_shows_when_nothing_cached_and_not_dismissed(
    root, monkeypatch
):
    view = _build_main_view(
        root, monkeypatch, onboarding_dismissed=False, report=_empty_report()
    )
    _pump_until(root, lambda: view._banner is not None)
    assert view._banner.winfo_exists()


def test_first_run_banner_suppressed_when_something_cached(root, monkeypatch):
    view = _build_main_view(
        root, monkeypatch, onboarding_dismissed=False, report=_cached_report()
    )
    _pump(root, 300)
    assert view._banner is None


def test_first_run_banner_suppressed_when_already_dismissed(root, monkeypatch):
    view = _build_main_view(
        root, monkeypatch, onboarding_dismissed=True, report=_empty_report()
    )
    _pump(root, 300)
    assert view._banner is None


def test_dismissing_banner_persists_onboarding_dismissed(root, monkeypatch):
    store = _FakeSettingsStore(Settings(onboarding_dismissed=False))
    monkeypatch.setattr(main_view_module, "SettingsStore", lambda: store)
    monkeypatch.setattr(
        resources_module, "build_resource_report", lambda models: _empty_report()
    )
    monkeypatch.setattr(
        resources_view_module, "build_resource_report", lambda models: _empty_report()
    )
    view = MainView(root)
    view.pack(fill="both", expand=True)
    _pump_until(root, lambda: view._banner is not None)

    view._dismiss_onboarding()

    assert store.saved
    assert store.saved[-1].onboarding_dismissed is True


def test_ctrl_shortcuts_route_to_correct_view(root, monkeypatch):
    view = _build_main_view(root, monkeypatch)
    # Key events only reach bindings on a window that actually has keyboard
    # focus -- the root fixture starts withdrawn, so make it visible first.
    root.deiconify()
    root.focus_force()
    _pump(root, 50)

    expected = [
        ("1", MainView.VIEW_CALCULATOR),
        ("2", MainView.VIEW_PARSER),
        ("3", MainView.VIEW_COMPARE),
        ("4", MainView.VIEW_REGISTRY),
        ("5", MainView.VIEW_RESOURCES),
    ]
    for key, view_id in expected:
        root.event_generate(f"<Control-Key-{key}>")
        _pump(root, 30)
        assert view._current_view == view_id


def test_escape_sets_active_view_cancel_event(root, monkeypatch):
    view = _build_main_view(root, monkeypatch)
    fake_view = type("FakeView", (), {"cancel_event": threading.Event()})()
    view._view_cache[MainView.VIEW_CALCULATOR] = fake_view
    view._current_view = MainView.VIEW_CALCULATOR

    view._cancel_active_work()

    assert fake_view.cancel_event.is_set()
