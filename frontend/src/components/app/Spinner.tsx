import { cn } from "@/lib/cn";

export interface SpinnerProps {
  size?: number;
  className?: string;
}

/**
 * Legible even when prefers-reduced-motion flattens the spin (see
 * motion.css): the ring shape itself communicates "loading", not just the
 * rotation.
 */
export function Spinner({ size = 16, className }: SpinnerProps) {
  return (
    <svg
      className={cn("animate-spin", className)}
      style={{ width: size, height: size }}
      viewBox="0 0 24 24"
      fill="none"
      role="status"
      aria-label="Loading"
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="3"
        strokeOpacity="0.25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
