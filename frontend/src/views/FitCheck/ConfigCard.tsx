import { AppSelect, type SelectOption } from "@/components/app/Select";
import { Card } from "@/components/app/Card";
import { HardwareBadge } from "@/components/app/HardwareBadge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { SectionLabel } from "@/components/app/SectionLabel";
import type { HardwareTarget, ModelArchitecture } from "@/lib/types";

export interface QuantOption {
  value: string;
  label: string;
}

export interface ConfigCardProps {
  architectures: ModelArchitecture[];
  hardware: HardwareTarget[];
  quantLevels: QuantOption[];
  kvDtypes: QuantOption[];
  architectureId: string;
  onArchitectureChange: (id: string) => void;
  hardwareId: string;
  onHardwareChange: (id: string) => void;
  quantization: string;
  onQuantizationChange: (v: string) => void;
  kvCacheDtype: string;
  onKvCacheDtypeChange: (v: string) => void;
  context: string;
  onContextChange: (v: string) => void;
  contextValid: boolean;
}

export function ConfigCard({
  architectures,
  hardware,
  quantLevels,
  kvDtypes,
  architectureId,
  onArchitectureChange,
  hardwareId,
  onHardwareChange,
  quantization,
  onQuantizationChange,
  kvCacheDtype,
  onKvCacheDtypeChange,
  context,
  onContextChange,
  contextValid,
}: ConfigCardProps) {
  // Vendors with no bundled brand mark (Qwen appears in several
  // architectures) get ProviderBadge's neutral default, so every row keeps
  // a leading badge -- a mixed icon/no-icon list looks broken.
  const modelOptions: SelectOption[] = architectures.map((a) => ({
    value: a.id,
    label: a.display_name,
    badge: <ProviderBadge provider={a.vendor} />,
  }));
  const hardwareOptions: SelectOption[] = hardware.map((h) => ({
    value: h.id,
    label: h.display_name,
    badge: <HardwareBadge vendor={h.vendor} />,
  }));
  const quantOptions: SelectOption[] = quantLevels.map((q) => ({ value: q.value, label: q.label }));
  const kvOptions: SelectOption[] = kvDtypes.map((d) => ({ value: d.value, label: d.label }));

  return (
    <Card className="p-4">
      <SectionLabel className="mb-3">Configuration</SectionLabel>

      <div className="mb-4 flex flex-col gap-2">
        <Label htmlFor="fit-model" className="type-body font-bold text-muted-foreground">
          Model
        </Label>
        <AppSelect
          id="fit-model"
          options={modelOptions}
          value={architectureId}
          onChange={onArchitectureChange}
          label="Model"
        />
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor="fit-quant" className="type-body font-bold text-muted-foreground">
            Weight quantization
          </Label>
          <AppSelect
            id="fit-quant"
            options={quantOptions}
            value={quantization}
            onChange={onQuantizationChange}
            label="Weight quantization"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="fit-kv" className="type-body font-bold text-muted-foreground">
            KV cache precision
          </Label>
          <AppSelect
            id="fit-kv"
            options={kvOptions}
            value={kvCacheDtype}
            onChange={onKvCacheDtypeChange}
            label="KV cache precision"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor="fit-context" className="type-body font-bold text-muted-foreground">
            Context needed
          </Label>
          <Input
            id="fit-context"
            value={context}
            onChange={(e) => onContextChange(e.target.value)}
            aria-invalid={!contextValid}
            className="font-mono"
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="fit-hardware" className="type-body font-bold text-muted-foreground">
            Hardware
          </Label>
          <AppSelect
            id="fit-hardware"
            options={hardwareOptions}
            value={hardwareId}
            onChange={onHardwareChange}
            label="Hardware"
          />
        </div>
      </div>
    </Card>
  );
}
