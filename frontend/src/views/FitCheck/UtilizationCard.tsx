import { Card } from "@/components/app/Card";
import { ContextBar } from "@/components/app/ContextBar";
import { contextLevel, fmtContextPct } from "@/lib/format";
import { cn } from "@/lib/cn";

export interface UtilizationCardProps {
  pct: number | null;
}

export function UtilizationCard({ pct }: UtilizationCardProps) {
  const level = contextLevel(pct);
  const colorClass =
    level === "over" ? "text-destructive" : level === "warn" ? "text-warning" : "text-foreground";

  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center justify-between">
        <p className="type-label font-bold text-foreground">VRAM utilization</p>
        <p className={cn("type-label tabular font-bold", colorClass)}>{fmtContextPct(pct)}</p>
      </div>
      <ContextBar pct={pct} />
    </Card>
  );
}
