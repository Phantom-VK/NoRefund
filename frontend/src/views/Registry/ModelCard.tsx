import * as React from "react";
import { ExternalLink, Hash } from "lucide-react";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { bridge } from "@/lib/bridge";
import { fmtContextWindow, fmtCost } from "@/lib/format";
import type { ModelInfo } from "@/lib/types";

export interface ModelCardProps {
  model: ModelInfo;
}

const KNOWN_PROVIDERS = new Set([
  "openai",
  "anthropic",
  "google",
  "deepseek",
  "meta",
  "mistral",
]);

function providerKey(provider: string): string {
  return KNOWN_PROVIDERS.has(provider.toLowerCase()) ? provider.toLowerCase() : "default";
}

function PriceCell({ label, price }: { label: string; price: number }) {
  return (
    <div className="rounded-md bg-muted px-2 py-2">
      <p className="type-micro text-muted-foreground">{label}</p>
      <p className="type-label tabular font-mono font-semibold text-card-foreground">
        {fmtCost(price)}
      </p>
    </div>
  );
}

export function ModelCard({ model }: ModelCardProps) {
  const accent = `var(--provider-${providerKey(model.provider)}-fg)`;

  function handleDocsClick(e: React.MouseEvent) {
    e.preventDefault();
    if (model.docs_url) void bridge.openUrl(model.docs_url);
  }

  return (
    <div className="overflow-hidden rounded-xl bg-card text-card-foreground">
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ background: `color-mix(in srgb, ${accent} 9%, var(--card))` }}
      >
        <div className="min-w-0">
          <p className="type-title truncate">{model.display_name}</p>
          <p className="type-small font-mono text-muted-foreground">{model.id}</p>
        </div>
        <ProviderBadge provider={model.provider} />
      </div>

      <div className="flex flex-col gap-3 px-4 py-3">
        <div>
          <p className="type-small text-muted-foreground">Context window</p>
          <p className="type-title tabular font-mono">
            {fmtContextWindow(model.context_window)}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <PriceCell label="Input / 1M" price={model.input_price_per_million} />
          <PriceCell label="Output / 1M" price={model.output_price_per_million} />
        </div>

        <div className="flex items-center justify-between border-t border-border pt-2">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Hash size={12} aria-hidden="true" />
            <span className="type-small font-mono">{model.tokenizer_name}</span>
          </div>
          {model.docs_url && (
            <a
              href={model.docs_url}
              onClick={handleDocsClick}
              className="flex items-center gap-1 text-muted-foreground transition-colors hover:text-primary"
              aria-label={`Docs for ${model.display_name}`}
            >
              <span className="type-small">Docs</span>
              <ExternalLink size={12} aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
