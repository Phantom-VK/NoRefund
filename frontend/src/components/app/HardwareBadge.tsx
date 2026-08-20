import { HardwareLogo } from "./hardware-logos";

export interface HardwareBadgeProps {
  vendor: string;
}

// Icon-only, unlike ProviderBadge's text pill -- hardware display names
// (e.g. "NVIDIA A100 80GB") already spell out the vendor, so a repeated
// text label next to it would be redundant. No tinted background either:
// each mark already carries its own brand color, and a background chosen
// to keep muted-but-accessible text legible made the icon read as dull and
// dark instead of the bright original mark.
export function HardwareBadge({ vendor }: HardwareBadgeProps) {
  return (
    <span
      className="inline-flex size-5 shrink-0 items-center justify-center rounded-full bg-secondary"
      title={vendor}
    >
      <HardwareLogo vendor={vendor} size={13} />
    </span>
  );
}
