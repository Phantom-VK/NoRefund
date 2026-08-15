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
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

_ZENITY = "zenity"
_USER_CANCELLED = 1
_POLL_INTERVAL_S = 0.05


def _zenity_available() -> bool:
    return sys.platform.startswith("linux") and shutil.which(_ZENITY) is not None


def _filter_args(filetypes: list[tuple[str, str]]) -> list[str]:
    args = []
    for label, patterns in filetypes:
        args += ["--file-filter", f"{label} | {patterns}"]
    return args


def _run_zenity(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Like `subprocess.run(capture_output=True, text=True)`, but pumps the
    Tk event loop while zenity is open. `subprocess.run` blocks the whole
    interpreter until the child exits, which stops the main window from
    repainting -- it visibly freezes under most Linux compositors -- for as
    long as the dialog stays open. Polling with `Popen` instead lets Tk
    keep processing its own events in between checks, the same nested-loop
    approach Tk's own native dialogs use internally.
    """
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    root = tk._default_root
    while proc.poll() is None:
        if root is not None:
            root.update()
        time.sleep(_POLL_INTERVAL_S)
    stdout, stderr = proc.communicate()
    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)


def ask_open_files(filetypes: list[tuple[str, str]]) -> list[str]:
    if _zenity_available():
        result = _run_zenity(
            [_ZENITY, "--file-selection", "--multiple", "--separator=\n"]
            + _filter_args(filetypes)
        )
        if result.returncode == 0:
            return [p for p in result.stdout.strip().split("\n") if p]
        if result.returncode == _USER_CANCELLED:
            return []
    return list(filedialog.askopenfilenames(filetypes=filetypes))


def ask_directory() -> str:
    if _zenity_available():
        result = _run_zenity([_ZENITY, "--file-selection", "--directory"])
        if result.returncode == 0:
            return result.stdout.strip()
        if result.returncode == _USER_CANCELLED:
            return ""
    return filedialog.askdirectory()


def ask_save_file(*, defaultextension: str, filetypes: list[tuple[str, str]]) -> str:
    if _zenity_available():
        result = _run_zenity(
            [_ZENITY, "--file-selection", "--save", "--confirm-overwrite"]
            + _filter_args(filetypes)
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            # Unlike filedialog.asksaveasfilename below, zenity has no
            # concept of defaultextension -- a name typed with no suffix
            # would otherwise save with none at all.
            if defaultextension and not Path(path).suffix:
                path += defaultextension
            return path
        if result.returncode == _USER_CANCELLED:
            return ""
    return filedialog.asksaveasfilename(
        defaultextension=defaultextension, filetypes=filetypes
    )
