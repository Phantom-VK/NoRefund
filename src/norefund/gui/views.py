"""Compatibility exports for GUI view classes.

New code should import directly from the focused modules:
``main_view``, ``calculator_view``, ``parser_view``, and ``registry_view``.
"""

from norefund.gui.calculator_view import CalculatorView
from norefund.gui.main_view import MainView
from norefund.gui.parser_view import LogsPanel, ParserView, ResultsTable
from norefund.gui.registry_view import RegistryView
from norefund.gui.settings_modal import SettingsModal
from norefund.gui.theme import COLORS, PROVIDER_COLORS, SUPPORTED_FILETYPES
from norefund.gui.widgets import (
    ContextBar,
    IconButton,
    ModelDropdown,
    SidebarItem,
    StatPill,
)

__all__ = [
    "CalculatorView",
    "COLORS",
    "ContextBar",
    "IconButton",
    "LogsPanel",
    "MainView",
    "ModelDropdown",
    "PROVIDER_COLORS",
    "ParserView",
    "RegistryView",
    "ResultsTable",
    "SettingsModal",
    "SidebarItem",
    "StatPill",
    "SUPPORTED_FILETYPES",
]
