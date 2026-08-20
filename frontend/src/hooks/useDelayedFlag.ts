import { useEffect, useState } from "react";

/** True only once `active` has stayed true for `delayMs` -- a loading
 *  spinner gated on this instead of `active` directly never flashes for a
 *  load that resolves before the delay (states matrix rule: "where the
 *  duration is predictable and short, show nothing; a flash of spinner is
 *  worse than a brief pause"). */
export function useDelayedFlag(active: boolean, delayMs = 200): boolean {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (!active) {
      setShown(false);
      return;
    }
    const timer = setTimeout(() => setShown(true), delayMs);
    return () => clearTimeout(timer);
  }, [active, delayMs]);

  return shown;
}
