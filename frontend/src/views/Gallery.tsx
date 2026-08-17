import { FileText, Sparkles } from "lucide-react";
import { Button } from "@/components/app/Button";
import { Card } from "@/components/app/Card";
import { StatPill } from "@/components/app/StatPill";
import { ContextBar } from "@/components/app/ContextBar";
import { ProviderBadge } from "@/components/app/ProviderBadge";
import { EmptyState } from "@/components/app/EmptyState";
import { Spinner } from "@/components/app/Spinner";
import { SectionLabel } from "@/components/app/SectionLabel";
import { useTheme } from "@/hooks/useTheme";

const PROVIDERS = [
  "OpenAI",
  "Anthropic",
  "Google",
  "DeepSeek",
  "Meta",
  "Mistral",
  "Qwen", // unknown provider — exercises the --provider-default-* fallback
];

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <SectionLabel>{title}</SectionLabel>
      <div className="flex flex-wrap items-center gap-3">{children}</div>
    </section>
  );
}

export default function Gallery() {
  const { mode, resolved, setMode } = useTheme();

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col gap-8 overflow-y-auto px-6 py-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="type-display">Component gallery</h1>
          <p className="type-body text-muted-foreground">
            Dev-only proof surface for the design system. Resolved theme:{" "}
            <span className="tabular">{resolved}</span>.
          </p>
        </div>
        <div className="flex gap-2">
          {(["light", "dark", "system"] as const).map((m) => (
            <Button
              key={m}
              variant={mode === m ? "primary" : "secondary"}
              onClick={() => setMode(m)}
            >
              {m}
            </Button>
          ))}
        </div>
      </header>

      <Section title="Button — variants">
        <Button variant="primary">Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="danger">Danger</Button>
      </Section>

      <Section title="Button — states">
        <Button variant="primary" icon={Sparkles}>
          With icon
        </Button>
        <Button variant="primary" loading>
          Loading
        </Button>
        <Button variant="primary" disabled>
          Disabled
        </Button>
        <Button variant="danger" disabled>
          Danger disabled
        </Button>
      </Section>

      <Section title="Card">
        <Card className="w-64 p-4">
          <p className="type-title">Plain card</p>
          <p className="type-body text-muted-foreground">
            Neutral surface, no accent.
          </p>
        </Card>
        <Card accent className="w-64 p-4">
          <p className="type-title">Accented card</p>
          <p className="type-body text-muted-foreground">
            3px primary strip on the left edge only — the surface itself
            never recolours (GUI_REVIEW.md §4.1).
          </p>
        </Card>
      </Section>

      <Section title="StatPill">
        <StatPill label="Tokens" value="128,400" mono />
        <StatPill label="Provider" value="OpenAI" />
      </Section>

      <Section title="ContextBar — 10% / 80% / 120%">
        <div className="flex w-full flex-col gap-2">
          <ContextBar pct={10} />
          <ContextBar pct={80} />
          <ContextBar pct={120} />
        </div>
      </Section>

      <Section title="ProviderBadge — known + fallback">
        {PROVIDERS.map((p) => (
          <ProviderBadge key={p} provider={p} />
        ))}
      </Section>

      <Section title="Spinner">
        <Spinner size={16} />
        <Spinner size={24} />
        <Spinner size={32} />
      </Section>

      <Section title="EmptyState">
        <div className="w-full">
          <EmptyState
            icon={FileText}
            title="No files yet"
            description="Add files and click Analyze to see results here."
            action={<Button variant="primary">Add files</Button>}
          />
        </div>
      </Section>
    </div>
  );
}
