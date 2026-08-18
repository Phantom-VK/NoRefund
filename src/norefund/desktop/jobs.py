"""Background jobs for the desktop bridge: progress, cancellation, results.

Every long-running `core` call runs here on a worker thread so the webview's
UI thread is never blocked. Workers receive a `threading.Event` for
cooperative cancellation and a `report` callback for progress — matching the
`cancel_event` / `on_progress` parameters `core` already exposes.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from norefund.desktop.dto import to_jsonable

logger = logging.getLogger(__name__)

Worker = Callable[[threading.Event, Callable[[Any], None]], Any]


@dataclass(frozen=True)
class JobEvent:
    job_id: str
    kind: str  # "progress" | "done" | "error" | "cancelled"
    payload: Any


class JobManager:
    """Runs workers on daemon threads and emits their lifecycle events."""

    def __init__(self, emit: Callable[[JobEvent], None]) -> None:
        self._emit = emit
        self._cancels: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def _safe_emit(self, event: JobEvent) -> None:
        # The window may have been destroyed while the job was running;
        # evaluate_js then raises. Losing an event is fine, crashing is not.
        try:
            self._emit(event)
        except Exception:  # noqa: BLE001
            logger.debug("dropped job event %s/%s", event.job_id, event.kind)

    def start(self, fn: Worker) -> str:
        job_id = uuid.uuid4().hex
        cancel = threading.Event()
        with self._lock:
            self._cancels[job_id] = cancel

        def run() -> None:
            try:
                result = fn(cancel, lambda p: self._safe_emit(
                    JobEvent(job_id, "progress", to_jsonable(p))
                ))
            except KeyboardInterrupt:
                self._safe_emit(JobEvent(job_id, "cancelled", None))
            except Exception as exc:  # noqa: BLE001
                logger.exception("job %s failed", job_id)
                self._safe_emit(JobEvent(job_id, "error", {"message": str(exc)}))
            else:
                if cancel.is_set():
                    self._safe_emit(JobEvent(job_id, "cancelled", None))
                else:
                    self._safe_emit(JobEvent(job_id, "done", to_jsonable(result)))
            finally:
                with self._lock:
                    self._cancels.pop(job_id, None)

        threading.Thread(target=run, daemon=True, name=f"job-{job_id[:8]}").start()
        return job_id

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancels.get(job_id)
        if event is None:
            return False
        event.set()
        return True

    def shutdown(self) -> None:
        with self._lock:
            for event in self._cancels.values():
                event.set()
            self._cancels.clear()
