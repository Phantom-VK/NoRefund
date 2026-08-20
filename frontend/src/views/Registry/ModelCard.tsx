import * as React from "react";
import { ExternalLink, Hash } from "lucide-react";
import { Card, CardBadge, CardTopRow, type CardArt } from "@/components/app/Card";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { KNOWN_PROVIDERS, ProviderLogo } from "@/components/app/provider-logos";
import { bridge } from "@/lib/bridge";
import { convertCurrency } from "@/lib/costing";
import { fmtContextWindow, fmtCostIn } from "@/lib/format";
import type { ExchangeRates, ModelInfo } from "@/lib/types";

export interface ModelCardProps {
  model: ModelInfo;
  /** Display currency (settings.currency) -- prices are converted into this
   *  from the model's USD list price before rendering. */
  currency: string;
  rates: ExchangeRates;
}

// Picked per provider (not the fixed six-item Gallery demo mapping) so each
// brand reads consistently across the grid; providers past the sixth reuse
// an art variant -- the corner illustration is a texture, not an identity
// signal on its own (the logo + colour already are).
const PROVIDER_ART: Record<string, CardArt> = {
  openai: "contours",
  anthropic: "dots-flow",
  google: "chevron",
  deepseek: "dots",
  meta: "stripes",
  mistral: "dashes",
  qwen: "contours",
};

function providerKey(provider: string): string {
  const key = provider.toLowerCase();
  return (KNOWN_PROVIDERS as readonly string[]).includes(key) ? key : "default";
}

function PriceCell({
  label,
  priceUsd,
  currency,
  rates,
}: {
  label: string;
  priceUsd: number;
  currency: string;
  rates: ExchangeRates;
}) {
  return (
    <div className="rounded-md bg-muted px-2 py-2">
      <p className="type-micro text-muted-foreground">{label}</p>
      <p className="type-label tabular font-mono font-semibold text-card-foreground">
        {fmtCostIn(convertCurrency(priceUsd, currency, rates), currency)}
      </p>
    </div>
  );
}

export function ModelCard({ model, currency, rates }: ModelCardProps) {
  const key = providerKey(model.provider);
  const hasLogo = key !== "default";
  // -bg/-fg is the pairing contrast.test.ts actually verifies (4.5:1+ in
  // both themes) -- using -fg as the badge's own background, as a first cut
  // of this card did, put a white icon on the *light* dark-theme tint
  // (e.g. anthropic's dark -fg is a light tan), measuring 2.27:1.
  const badgeBg = `var(--provider-${key}-bg)`;
  const badgeFg = `var(--provider-${key}-fg)`;
  const art = PROVIDER_ART[key] ?? "dots";
  // The award-card reference these illustrations came from is sparse (one
  // headline + a date); this card is dense with pricing data, so the same
  // full-strength art reads as noise across the price cells and Docs link
  // instead of a background flourish. Feed card-art.css an already-faded
  // input color so its own internal color-mix() layers land much lighter.
  const artAccent = `color-mix(in srgb, ${badgeFg} 8%, transparent)`;

  function handleDocsClick(e: React.MouseEvent) {
    e.preventDefault();
    if (!model.docs_url) return;
    // Fire-and-forget from a click handler -- still worth swallowing a
    // rejection (bridge not ready yet, webbrowser.open failing) so it
    // doesn't surface as an unhandled promise rejection in devtools.
    bridge.openUrl(model.docs_url).catch(() => {});
  }

  return (
    <Card art={art} artColor={artAccent} className="min-w-0">
      <CardTopRow className="mb-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <CardBadge
            className="size-9 shrink-0 rounded-lg"
            style={{ background: badgeBg, color: badgeFg }}
          >
            {hasLogo ? (
              <ProviderLogo provider={model.provider} size={17} />
            ) : (
              <span className="type-small font-semibold" aria-hidden="true">
                {model.provider.charAt(0).toUpperCase()}
              </span>
            )}
          </CardBadge>
          <div className="min-w-0">
            <p className="type-title truncate">{model.display_name}</p>
            <p className="type-small truncate font-mono text-muted-foreground">
              {model.id}
            </p>
          </div>
        </div>
        <ProviderBadge provider={model.provider} />
      </CardTopRow>

      <div>
        <p className="type-small text-muted-foreground">Context window</p>
        <p className="type-title tabular font-mono">
          {fmtContextWindow(model.context_window)}
        </p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <PriceCell
          label="Input / 1M"
          priceUsd={model.input_price_per_million}
          currency={currency}
          rates={rates}
        />
        <PriceCell
          label="Output / 1M"
          priceUsd={model.output_price_per_million}
          currency={currency}
          rates={rates}
        />
      </div>

      <div className="mt-auto flex items-center justify-between border-t border-border pt-2">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Hash size={12} aria-hidden="true" />
          <span className="type-small font-mono">{model.tokenizer_name}</span>
        </div>
        {model.docs_url && (
          <a
            href={model.docs_url}
            onClick={handleDocsClick}
            className="flex items-center gap-1 rounded text-muted-foreground outline-none transition-colors hover:text-primary focus-visible:ring-[3px] focus-visible:ring-ring/50"
            aria-label={`Docs for ${model.display_name}`}
          >
            <span className="type-small">Docs</span>
            <ExternalLink size={12} aria-hidden="true" />
          </a>
        )}
      </div>
    </Card>
  );
}
