"""Application-wide structured JSON logging.

This module exposes a single `get_logger()` function that returns a
`logging.Logger` configured to:

- emit **JSON lines** (one JSON object per log line)
- include standard fields: timestamp, level, file, line, message
- include optional context fields via extra={"ctx": {...}}
- write logs to a per-user log directory (platform aware)

Usage:

    from norefund.logging_config import get_logger

    log = get_logger(__name__)
    log.info("analysed file", extra={"ctx": {"path": str(path), "tokens": 123}})

The GUI uses the same logger and the log viewer simply tails the latest
log file.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Log directory helpers
# ---------------------------------------------------------------------------


def _default_log_dir() -> Path:
    """Return platform-appropriate log directory for the current user.

    - Linux/macOS: ~/.norefund/logs
    - Windows:     %LOCALAPPDATA%/NoRefund/logs
    """

    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "NoRefund" / "logs"
    return Path.home() / ".norefund" / "logs"


LOG_DIR: Path = _default_log_dir()
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass


def latest_log_file() -> Path | None:
    """Return the most recent log file in LOG_DIR, or None if empty."""

    if not LOG_DIR.exists():
        return None
    files = sorted(LOG_DIR.glob("*.log"))
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
    ctx: dict[str, Any]


class JsonFormatter(logging.Formatter):
    """Format records as JSON lines with a controlled schema."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        # Base context passed via extra={"ctx": {...}}
        ctx = getattr(record, "ctx", {})
        if not isinstance(ctx, dict):
            ctx = {"value": repr(ctx)}

        data = LogRecordData(
            ts=datetime.utcfromtimestamp(record.created).isoformat() + "Z",
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


def _build_handler() -> logging.Handler:
    """Create a rotating file handler in the user log directory."""

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return logging.NullHandler()
    logfile = LOG_DIR / "norefund.log"

    try:
        handler = logging.handlers.RotatingFileHandler(
            logfile,
            maxBytes=5 * 1024 * 1024,  # 5 MB per file
            backupCount=3,
            encoding="utf-8",
        )
    except OSError:
        return logging.NullHandler()
    handler.setFormatter(JsonFormatter())
    return handler


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a module-level logger with JSON file handler attached.

    The first call initialises root-level settings, subsequent calls reuse
    the same handler and configuration.
    """

    logger_name = name or "norefund"
    if logger_name in _LOGGERS:
        return _LOGGERS[logger_name]

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Attach a single shared handler to the root app logger only once.
    root = logging.getLogger("norefund")
    if not root.handlers:
        handler = _build_handler()
        root.addHandler(handler)
        root.setLevel(logging.INFO)

    if logger is not root:
        logger.propagate = True
    _LOGGERS[logger_name] = logger
    return logger
