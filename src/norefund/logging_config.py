"""Application-wide structured JSON logging.

This module exposes a single `get_logger()` function that returns a
`logging.Logger` configured to:

- emit **JSON lines** (one JSON object per log line)
- include standard fields: timestamp, level, file, line, message
- include optional context fields via extra={"ctx": {...}}
- write logs to a per-user log directory (platform aware)
- create **one log file per app run**, named with a UTC timestamp
- delete the run's log file on exit if nothing was ever written

Usage:

    from norefund.logging_config import get_logger

    log = get_logger(__name__)
    log.info("analysed_file", extra={"ctx": {"path": str(path), "tokens": 123}})

The GUI uses the same logger and the log viewer lets the user pick any
run's log file from a dropdown.
"""

from __future__ import annotations

import atexit
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from norefund.core.paths import app_log_dir


# ---------------------------------------------------------------------------
# Log directory helpers
# ---------------------------------------------------------------------------


def _legacy_log_dir() -> Path:
    """Old, pre-platformdirs log location — kept only so it can be surfaced
    in the Resources view. New runs never write here.

    - Linux/macOS: ~/.norefund/logs
    - Windows:     %LOCALAPPDATA%/NoRefund/logs
    """

    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "NoRefund" / "logs"
    return Path.home() / ".norefund" / "logs"


LEGACY_LOG_DIR: Path = _legacy_log_dir()

LOG_DIR: Path = app_log_dir()
LOG_DIR.mkdir(parents=True, exist_ok=True)

# One log file per app run, timestamped in UTC
_RUN_TS = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
RUN_LOG_FILE: Path = LOG_DIR / f"norefund-{_RUN_TS}.log"


def list_log_files() -> List[Path]:
    """Return all known run log files, sorted by name (oldest → newest)."""

    if not LOG_DIR.exists():
        return []
    return sorted(LOG_DIR.glob("norefund-*.log"))


def latest_log_file() -> Optional[Path]:
    """Return the most recent run log file, or None if none exist."""

    files = list_log_files()
    return files[-1] if files else None


# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

@dataclass
class LogRecordData:
    ts: str
    level: str
    logger: str
    message: str
    module: str
    func: str
    line: int
    pathname: str
    ctx: Dict[str, Any]


class JsonFormatter(logging.Formatter):
    """Format records as JSON lines with a controlled schema."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        ctx = getattr(record, "ctx", {})
        if not isinstance(ctx, dict):
            ctx = {"value": repr(ctx)}

        data = LogRecordData(
            ts=datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            level=record.levelname,
            logger=record.name,
            message=str(record.getMessage()),
            module=record.module,
            func=record.funcName,
            line=record.lineno,
            pathname=record.pathname,
            ctx=ctx,
        )
        return json.dumps(asdict(data), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

_LOGGERS: dict[str, logging.Logger] = {}
_HANDLER_INITIALISED = False


def _build_handler() -> logging.Handler:
    """Create a file handler for this run's log file."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(RUN_LOG_FILE, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    return handler


def _register_atexit_cleanup() -> None:
    """Register a cleanup hook that deletes empty run log files.

    If the app starts and exits without ever writing a log line,
    we don't want to leave behind an empty `norefund-*.log` file.
    """

    def _cleanup() -> None:
        try:
            if RUN_LOG_FILE.exists() and RUN_LOG_FILE.stat().st_size == 0:
                RUN_LOG_FILE.unlink()
        except OSError:
            # Best-effort only; ignore failures.
            pass

    atexit.register(_cleanup)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a module-level logger with JSON file handler attached.

    The first call initialises root-level settings, subsequent calls reuse
    the same handler and configuration.
    """

    global _HANDLER_INITIALISED

    logger_name = name or "norefund"
    if logger_name in _LOGGERS:
        return _LOGGERS[logger_name]

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    root = logging.getLogger("norefund")
    if not _HANDLER_INITIALISED:
        root.addHandler(_build_handler())
        root.setLevel(logging.INFO)
        _register_atexit_cleanup()
        _HANDLER_INITIALISED = True

    if logger is not root:
        logger.propagate = True
    _LOGGERS[logger_name] = logger
    return logger
