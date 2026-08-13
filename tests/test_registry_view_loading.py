"""Smoke tests for RegistryView's loading-text / atomic-reveal flow.

Requires a real or virtual (e.g. Xvfb) X11 display. Skips cleanly when
none is available, matching CLAUDE.md's "GUI issues verified manually"
policy while still giving CI something to run when a display exists.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

ctk = pytest.importorskip("customtkinter")

from norefund.core.models_registry import list_models  # noqa: E402
from norefund.gui.registry_view import RegistryView  # noqa: E402

from .conftest import _pump, _pump_until  # noqa: E402

# LoadingOverlay.hide() fades its text color out over ~150ms (motion.py's
# fade_text_color) before calling place_forget(), so the label is still
# placed for a moment after `_loading` flips False -- pump past the fade
# before asserting it's gone.
_FADE_SETTLE_MS = 250


@dataclass
class _FakeShell:
    models: list


def test_loading_text_shows_first_then_atomic_reveal(root):
    shell = _FakeShell(models=list_models())
    view = RegistryView(root, shell)

    relayout_calls: list[list] = []
    original_relayout = view._relayout

    def spy_relayout(force=False):
        relayout_calls.append(list(view._cards))
        return original_relayout(force)

    view._relayout = spy_relayout

    # Right after construction (before any event-loop tick), loading must
    # already be showing and no cards built yet -- _start_loading() sets
    # this up synchronously in __init__.
    assert view._loading is True
    assert view._cards == []
    assert view._loading_overlay._label.place_info() != {}

    _pump_until(root, lambda: not view._loading)
    _pump(root, _FADE_SETTLE_MS)

    assert view._loading_overlay._label.place_info() == {}
    assert len(view._cards) == len(shell.models)
    for _model, card in view._cards:
        assert card.grid_info() != {}

    # Cards only ever get gridded once all of them are built -- there must
    # be no _relayout call while some cards exist and others don't (that
    # would mean a partial/progressive reveal, which is the jank we removed).
    assert relayout_calls, "expected at least one _relayout call"
    for snapshot in relayout_calls:
        assert len(snapshot) in (0, len(shell.models))

    final_cards = [card for _model, card in relayout_calls[-1]]
    assert len(final_cards) == len(shell.models)


def test_navigating_away_mid_load_does_not_crash(root):
    shell = _FakeShell(models=list_models())
    view = RegistryView(root, shell)
    assert view._loading is True
    # Destroy before the event loop has ticked at all, so the next-card
    # callback scheduled in _start_loading() is still pending in Tcl's
    # queue when the widget goes away.
    view.destroy()
    # That pending after() callback must not raise once its target widget
    # is gone.
    _pump(root, 300)


def test_zero_models_does_not_crash(root):
    shell = _FakeShell(models=[])
    view = RegistryView(root, shell)
    _pump_until(root, lambda: not view._loading)
    assert view._cards == []
