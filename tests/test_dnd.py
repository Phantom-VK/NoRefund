from __future__ import annotations

from pathlib import Path

from norefund.gui.dnd import parse_dropped_paths


def test_parse_dropped_paths_simple():
    assert parse_dropped_paths("/tmp/a.pdf /tmp/b.txt") == [
        Path("/tmp/a.pdf"),
        Path("/tmp/b.txt"),
    ]


def test_parse_dropped_paths_with_spaces_in_braces():
    data = "{/tmp/my file.pdf} /tmp/other.txt"
    assert parse_dropped_paths(data) == [
        Path("/tmp/my file.pdf"),
        Path("/tmp/other.txt"),
    ]


def test_parse_dropped_paths_single_braced_path():
    assert parse_dropped_paths("{/tmp/dir with space}") == [
        Path("/tmp/dir with space")
    ]


def test_parse_dropped_paths_empty():
    assert parse_dropped_paths("") == []
