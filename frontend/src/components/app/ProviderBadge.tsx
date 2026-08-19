export interface ProviderBadgeProps {
  provider: string;
}

const KNOWN_PROVIDERS = new Set([
  "openai",
  "anthropic",
  "google",
  "deepseek",
  "meta",
  "mistral",
  "qwen",
]);

export function ProviderBadge({ provider }: ProviderBadgeProps) {
  const key = KNOWN_PROVIDERS.has(provider.toLowerCase())
    ? provider.toLowerCase()
    : "default";

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
