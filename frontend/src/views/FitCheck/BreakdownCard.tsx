import { Card } from "@/components/app/Card";
import { StatPill } from "@/components/app/StatPill";
import { fmtBytes, fmtHeadroom } from "@/lib/format";
import type { MemoryEstimate } from "@/lib/types";

export interface BreakdownCardProps {
  estimate: MemoryEstimate | null;
  headroomBytes: number | null;
}

export function BreakdownCard({ estimate, headroomBytes }: BreakdownCardProps) {
  return (
    <Card className="p-4">
      <div className="grid grid-cols-3 gap-3">
        <StatPill label="Weights" value={fmtBytes(estimate?.weights_bytes ?? null)} mono />
        <StatPill label="KV cache" value={fmtBytes(estimate?.kv_cache_bytes ?? null)} mono />
        <StatPill label="Activations" value={fmtBytes(estimate?.activation_bytes ?? null)} mono />
        <StatPill label="Framework overhead" value={fmtBytes(estimate?.framework_overhead_bytes ?? null)} mono />
        <StatPill label="Total needed" value={fmtBytes(estimate?.total_bytes ?? null)} mono />
        <StatPill
          label="Headroom"
          value={fmtHeadroom(headroomBytes)}
          mono
          valueClassName={headroomBytes !== null && headroomBytes < 0 ? "text-destructive" : undefined}
        />
      </div>
    </Card>
  );
}
