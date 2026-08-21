import { CheckCircle, Info, XCircle } from "lucide-react";
import { Card } from "@/components/app/Card";
import { ContextBar } from "@/components/app/ContextBar";
import { contextLevel, fmtContextPct, fmtNum } from "@/lib/format";

export interface ContextCardProps {
  pct: number | null;
  inputTokens: number | null;
  contextWindow: number;
  /** null when inputTokens is invalid -- fit status is unknown, not "fits". */
  fits: boolean | null;
  showWarnings: boolean;
}

export function ContextCard({
  pct,
  inputTokens,
  contextWindow,
  fits,
  showWarnings,
}: ContextCardProps) {
  const level = contextLevel(pct);
  const neutral = "var(--muted-foreground)";
  const tierColor =
    level === "over" ? "var(--destructive)" : level === "warn" ? "var(--warning)" : "var(--primary)";
  const barColor = showWarnings ? tierColor : neutral;

  return (
    <Card>
      <div className="flex items-center justify-between">
        <p className="type-label font-semibold">Context window usage</p>
        <p className="type-label tabular font-semibold" style={{ color: barColor }}>
          {fmtContextPct(pct)}
        </p>
      </div>
      <ContextBar
        pct={pct}
        forceColor={barColor}
        className="mt-2"
        label="Context window usage"
      />
      <p className="type-body tabular mt-2 text-muted-foreground">
        {inputTokens === null ? "—" : fmtNum(inputTokens)} input tokens · of{" "}
        {fmtNum(contextWindow)} max
      </p>
      <div className="mt-2 flex items-center gap-2">
        {fits === null ? (
          <>
            <Info size={16} className="shrink-0 text-muted-foreground" aria-hidden="true" />
            <p className="type-label text-muted-foreground">Enter a valid input token count</p>
          </>
        ) : fits ? (
          <>
            <CheckCircle
              size={16}
              className="shrink-0"
              style={{ color: "var(--primary)" }}
              aria-hidden="true"
            />
            <p className="type-label text-muted-foreground">Fits in one context window</p>
          </>
        ) : (
          <>
            <XCircle
              size={16}
              className="shrink-0"
              style={{ color: showWarnings ? "var(--destructive)" : neutral }}
              aria-hidden="true"
            />
            <p className="type-label text-muted-foreground">
              Exceeds by {fmtNum(Math.max(0, (inputTokens ?? 0) - contextWindow))} tokens —
              chunking required
            </p>
          </>
        )}
      </div>
    </Card>
  );
}
