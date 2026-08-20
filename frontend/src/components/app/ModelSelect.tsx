import { AppSelect } from "./Select";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { modelLabel } from "@/lib/format";
import type { ModelInfo } from "@/lib/types";

export interface ModelSelectProps {
  models: ModelInfo[];
  /** Selected model id. */
  value: string;
  onChange: (model: ModelInfo) => void;
  className?: string;
  /** For associating an external <Label htmlFor>. */
  id?: string;
  disabled?: boolean;
  /** Accessible name. AppSelect sets this as aria-label, which wins over
   *  an associated <label htmlFor> in the accessible-name computation --
   *  pass the same text as that external label (e.g. "Model") so the
   *  announced name matches what's on screen. Defaults to a sensible name
   *  for callers with no visible label of their own (e.g. Parser's toolbar). */
  label?: string;
}

/** Thin wrapper over AppSelect: every row gets a leading ProviderBadge,
 *  including providers with no brand colour (ProviderBadge falls back to a
 *  neutral one), so rows stay aligned instead of a mixed icon/no-icon look. */
export function ModelSelect({ models, value, onChange, className, id, disabled, label = "Select a model" }: ModelSelectProps) {
  return (
    <AppSelect
      options={models.map((m) => ({
        value: m.id,
        label: modelLabel(m),
        badge: <ProviderBadge provider={m.provider} />,
      }))}
      value={value}
      onChange={(newId) => {
        const model = models.find((m) => m.id === newId);
        if (model) onChange(model);
      }}
      label={label}
      className={className}
      id={id}
      disabled={disabled}
    />
  );
}
