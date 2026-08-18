import { useCallback, useEffect, useRef, useState } from "react";
import { bridge, BridgeError } from "@/lib/bridge";
import type { JobEventDetail } from "@/lib/types";

export interface JobState<P, R> {
  jobId: string | null;
  running: boolean;
  progress: P[];
  result: R | null;
  error: string | null;
  cancelled: boolean;
  start: (starter: () => Promise<string>) => Promise<void>;
  cancel: () => void;
  reset: () => void;
}

/** Tracks one norefund:job event stream at a time. Events whose job_id
 *  doesn't match the current job are ignored, so a stale job from a
 *  previous run can never write into the current state. */
export function useJob<P = unknown, R = unknown>(): JobState<P, R> {
  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<P[]>([]);
  const [result, setResult] = useState<R | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelled, setCancelled] = useState(false);
  const jobIdRef = useRef<string | null>(null);

  useEffect(() => {
    const onJobEvent = (evt: Event) => {
      const { detail } = evt as CustomEvent<JobEventDetail>;
      if (!detail || detail.job_id !== jobIdRef.current) return;

      switch (detail.kind) {
        case "progress":
          setProgress((prev) => [...prev, detail.payload as P]);
          break;
        case "done":
          setResult(detail.payload as R);
          setRunning(false);
          break;
        case "error":
          setError((detail.payload as { message: string }).message);
          setRunning(false);
          break;
        case "cancelled":
          setCancelled(true);
          setRunning(false);
          break;
      }
    };

    window.addEventListener("norefund:job", onJobEvent);
    return () => window.removeEventListener("norefund:job", onJobEvent);
  }, []);

  const start = useCallback(async (starter: () => Promise<string>) => {
    setProgress([]);
    setResult(null);
    setError(null);
    setCancelled(false);
    setRunning(true);
    try {
      const id = await starter();
      jobIdRef.current = id;
      setJobId(id);
    } catch (err) {
      setRunning(false);
      setError(err instanceof BridgeError ? err.message : String(err));
    }
  }, []);

  const cancel = useCallback(() => {
    // running stays true until the "cancelled" event arrives, so the UI
    // can show "Cancelling…" rather than snapping back to idle early.
    if (jobIdRef.current) void bridge.cancelJob(jobIdRef.current);
  }, []);

  const reset = useCallback(() => {
    jobIdRef.current = null;
    setJobId(null);
    setRunning(false);
    setProgress([]);
    setResult(null);
    setError(null);
    setCancelled(false);
  }, []);

  return { jobId, running, progress, result, error, cancelled, start, cancel, reset };
}
