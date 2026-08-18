"""Background job lifecycle: progress, completion, failure, cancellation."""

from __future__ import annotations

import threading
import time

from norefund.desktop.jobs import JobEvent, JobManager


def _drain(events: list[JobEvent], kind: str, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for e in events:
            if e.kind == kind:
                return e
        time.sleep(0.01)
    raise AssertionError(f"no {kind!r} event within {timeout}s: {events}")


def test_successful_job_emits_progress_then_done():
    events: list[JobEvent] = []
    mgr = JobManager(emit=events.append)

    def work(cancel, report):
        report({"step": 1})
        return {"ok": True}

    job_id = mgr.start(work)
    done = _drain(events, "done")
    assert done.job_id == job_id
    assert done.payload == {"ok": True}
    assert any(e.kind == "progress" and e.payload == {"step": 1} for e in events)
    mgr.shutdown()


def test_failing_job_emits_error_with_the_message():
    events: list[JobEvent] = []
    mgr = JobManager(emit=events.append)

    def work(cancel, report):
        raise ValueError("kaboom")

    mgr.start(work)
    err = _drain(events, "error")
    assert "kaboom" in err.payload["message"]
    mgr.shutdown()


def test_cancelled_job_emits_cancelled_not_done():
    events: list[JobEvent] = []
    mgr = JobManager(emit=events.append)
    started = threading.Event()

    def work(cancel, report):
        started.set()
        while not cancel.is_set():
            time.sleep(0.01)
        raise KeyboardInterrupt

    job_id = mgr.start(work)
    started.wait(timeout=2)
    assert mgr.cancel(job_id) is True
    _drain(events, "cancelled")
    assert not any(e.kind == "done" for e in events)
    mgr.shutdown()


def test_cancelling_an_unknown_job_is_false_not_an_error():
    mgr = JobManager(emit=lambda _e: None)
    assert mgr.cancel("nope") is False
    mgr.shutdown()


def test_job_ids_are_unique():
    mgr = JobManager(emit=lambda _e: None)
    ids = {mgr.start(lambda c, r: None) for _ in range(20)}
    assert len(ids) == 20
    mgr.shutdown()


def test_emit_failures_do_not_kill_the_worker():
    # The window can be destroyed mid-job; evaluate_js then raises. A job
    # must not take the process down because the UI went away.
    def boom(_event):
        raise RuntimeError("window is gone")

    mgr = JobManager(emit=boom)
    mgr.start(lambda c, r: "fine")
    time.sleep(0.2)
    mgr.shutdown()
