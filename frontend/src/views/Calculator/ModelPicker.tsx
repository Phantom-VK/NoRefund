import { ModelSelect } from "@/components/app/ModelSelect";
import { Label } from "@/components/ui/label";
import type { ModelInfo } from "@/lib/types";

export interface ModelPickerProps {
  models: ModelInfo[];
  value: string;
  onChange: (model: ModelInfo) => void;
}

export function ModelPicker({ models, value, onChange }: ModelPickerProps) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="calc-model">Model</Label>
      <ModelSelect id="calc-model" models={models} value={value} onChange={onChange} label="Model" />
    </div>
  );
}
