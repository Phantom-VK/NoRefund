import { KNOWN_PROVIDERS } from "./provider-logos";

export interface ProviderBadgeProps {
  provider: string;
}

export function ProviderBadge({ provider }: ProviderBadgeProps) {
  const lower = provider.toLowerCase();
  const key = (KNOWN_PROVIDERS as readonly string[]).includes(lower) ? lower : "default";

  return (
    <span
      className="type-micro inline-flex items-center rounded-full px-2 py-0.5"
      style={{
        backgroundColor: `var(--provider-${key}-bg)`,
        color: `var(--provider-${key}-fg)`,
      }}
    >
      {provider}
    </span>
  );
}
