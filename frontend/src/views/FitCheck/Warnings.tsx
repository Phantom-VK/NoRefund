import { AlertTriangle } from "lucide-react";

export interface WarningsProps {
  warnings: readonly string[];
}

export function Warnings({ warnings }: WarningsProps) {
  if (warnings.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {warnings.map((message, i) => (
        <p key={i} className="type-body flex items-start gap-1.5 text-muted-foreground">
          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-warning" aria-hidden="true" />
          {message}
        </p>
      ))}
    </div>
  );
}
