import { Card } from "@/components/app/Card";
import { Checkbox } from "@/components/ui/checkbox";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { modelLabel } from "@/lib/format";
import type { ModelInfo } from "@/lib/types";

export interface ModelChecklistProps {
  models: ModelInfo[];
  selected: Set<string>;
  onChange: (selected: Set<string>) => void;
}

export function ModelChecklist({ models, selected, onChange }: ModelChecklistProps) {
  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  }

  return (
    <Card className="flex min-h-0 flex-1 flex-col p-4">
      <div className="mb-2 flex items-center justify-between">
        <p className="type-label text-foreground">Models · {selected.size} selected</p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="pressable type-small rounded text-primary outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            onClick={() => onChange(new Set(models.map((m) => m.id)))}
          >
            Select all
          </button>
          <button
            type="button"
            className="pressable type-small rounded text-primary outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            onClick={() => onChange(new Set())}
          >
            Select none
          </button>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto">
        {models.map((m) => (
          <label
            key={m.id}
            className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 hover:bg-muted"
          >
            <Checkbox checked={selected.has(m.id)} onCheckedChange={() => toggle(m.id)} />
            <ProviderBadge provider={m.provider} />
            <span className="type-small truncate text-foreground">{modelLabel(m)}</span>
          </label>
        ))}
      </div>
    </Card>
  );
}
