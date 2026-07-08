"""Smoke tests for RegistryView's skeleton-loading / atomic-reveal flow.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import pytest

ctk = pytest.importorskip("customtkinter")

from norefund.core.models_registry import list_models  # noqa: E402
from norefund.gui.registry_view import _MIN_SKELETON_MS, RegistryView  # noqa: E402


@dataclass
class _FakeShell:
    models: list


@pytest.fixture
def root():
    try:
        r = ctk.CTk()
        r.withdraw()
    except Exception as exc:  # no display available
        pytest.skip(f"no Tk display available: {exc}")
    yield r
    r.destroy()


def _pump(root, ms: int) -> None:
    deadline = time.monotonic() + ms / 1000
    while time.monotonic() < deadline:
        root.update()


def _pump_until(root, predicate, timeout_ms: int = 3000) -> None:
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        root.update()
        if predicate():
            return
    pytest.fail("condition not met within timeout")


def test_skeleton_shows_first_then_atomic_reveal(root):
    shell = _FakeShell(models=list_models())
    start = time.monotonic()
    view = RegistryView(root, shell)
    original_skeletons = list(view._skeletons)
    assert original_skeletons, "expected at least one skeleton card"

    relayout_calls: list[list] = []
    original_relayout = view._relayout

    def spy_relayout(force=False):
        relayout_calls.append(list(view._cards))
        return original_relayout(force)

    view._relayout = spy_relayout

    # Right after construction (before any event-loop tick), the skeleton
    # grid must already be showing -- _start_loading() sets this up
    # synchronously in __init__. We can't rely on catching a later "still
    # mid-load" moment via update(): under a slow display (e.g. Xvfb),
    # each real-card build takes longer than the 1ms scheduling delay, so
    # a single root.update() call can cascade through the whole build
    # chain before returning control here.
    assert view._loading is True
    assert all(card in original_skeletons for _model, card in view._cards)

    _pump_until(root, lambda: not view._loading)
    elapsed_ms = (time.monotonic() - start) * 1000
    assert elapsed_ms >= _MIN_SKELETON_MS - 20  # scheduler slack

    assert view._skeletons == []
    for skeleton in original_skeletons:
        assert skeleton.winfo_exists() == 0

    assert len(view._cards) == len(shell.models)
    for _model, card in view._cards:
        assert card not in original_skeletons
        assert card.grid_info() != {}

    # Every recorded _relayout call graded either all-skeleton or all-real
    # cards -- never a mix. That's what "atomic reveal" means here.
    assert relayout_calls, "expected at least one _relayout call"
    for snapshot in relayout_calls:
        cards_only = [card for _model, card in snapshot]
        is_all_skeleton = all(c in original_skeletons for c in cards_only)
        is_all_real = all(c not in original_skeletons for c in cards_only)
        assert is_all_skeleton or is_all_real

    final_cards = [card for _model, card in relayout_calls[-1]]
    assert final_cards and all(c not in original_skeletons for c in final_cards)


def test_navigating_away_mid_load_does_not_crash(root):
    shell = _FakeShell(models=list_models())
    view = RegistryView(root, shell)
    assert view._loading is True
    # Destroy before the event loop has ticked at all, so the dwell timer
    # and next-card-builder callbacks scheduled in _start_loading() are
    # still pending in Tcl's queue when the widget goes away.
    view.destroy()
    # Those pending after() callbacks must not raise once their target
    # widget is gone.
    _pump(root, 700)


def test_zero_models_does_not_crash(root):
    shell = _FakeShell(models=[])
    view = RegistryView(root, shell)
    _pump_until(root, lambda: not view._loading)
    assert view._cards == []
