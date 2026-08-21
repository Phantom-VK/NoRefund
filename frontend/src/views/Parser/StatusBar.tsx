export interface StatusBarProps {
  left: string | null;
  right: string | null;
}

/** Hidden until there is something to say -- no permanent empty strip. */
export function StatusBar({ left, right }: StatusBarProps) {
  if (!left) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center justify-between border-t border-border bg-card px-3 py-1.5"
    >
      <p className="type-small text-muted-foreground">{left}</p>
      {right && (
        <p className="type-small tabular font-mono text-muted-foreground">{right}</p>
      )}
    </div>
  );
}
