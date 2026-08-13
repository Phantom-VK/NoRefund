"""File pickers that prefer the desktop's native dialog over Tk's own.

Stock ``tkinter.filedialog`` opens Tk's built-in Tcl file browser on Linux,
not the desktop's real file manager -- unlike Windows/macOS, where tkinter
dialogs already are the native picker. When zenity is available (standard on
GNOME and most Linux desktops), shell out to it for the picker users already
know; fall back to the stock Tk dialog everywhere else (no zenity, a
non-Linux platform, or anything other than a clean cancel).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from tkinter import filedialog

_ZENITY = "zenity"
_USER_CANCELLED = 1


def _zenity_available() -> bool:
    return sys.platform.startswith("linux") and shutil.which(_ZENITY) is not None


def _filter_args(filetypes: list[tuple[str, str]]) -> list[str]:
    args = []
    for label, patterns in filetypes:
        args += ["--file-filter", f"{label} | {patterns}"]
    return args


def ask_open_files(filetypes: list[tuple[str, str]]) -> list[str]:
    if _zenity_available():
        result = subprocess.run(
            [_ZENITY, "--file-selection", "--multiple", "--separator=\n"]
            + _filter_args(filetypes),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return [p for p in result.stdout.strip().split("\n") if p]
        if result.returncode == _USER_CANCELLED:
            return []
    return list(filedialog.askopenfilenames(filetypes=filetypes))


def ask_directory() -> str:
    if _zenity_available():
        result = subprocess.run(
            [_ZENITY, "--file-selection", "--directory"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        if result.returncode == _USER_CANCELLED:
            return ""
    return filedialog.askdirectory()


def ask_save_file(*, defaultextension: str, filetypes: list[tuple[str, str]]) -> str:
    if _zenity_available():
        result = subprocess.run(
            [_ZENITY, "--file-selection", "--save", "--confirm-overwrite"]
            + _filter_args(filetypes),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        if result.returncode == _USER_CANCELLED:
            return ""
    return filedialog.asksaveasfilename(
        defaultextension=defaultextension, filetypes=filetypes
    )
