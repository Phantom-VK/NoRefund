import { useCallback, useEffect, useRef, useState } from "react";
import { BridgeError } from "@/lib/bridge";

export interface BridgeQueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Load-once data with loading/error state. Ignores a resolved promise if
 *  the component unmounted first. */
export function useBridgeQuery<T>(
  fn: () => Promise<T>,
  deps: React.DependencyList = [],
): BridgeQueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generation, setGeneration] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fnRef
      .current()
      .then((result) => {
        if (cancelled) return;
        setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof BridgeError ? err.message : String(err));
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generation, ...deps]);

  const reload = useCallback(() => setGeneration((g) => g + 1), []);

  return { data, loading, error, reload };
}
