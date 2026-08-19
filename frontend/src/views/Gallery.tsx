import { FileText, Sparkles, Trophy, Star, Gem, Play, Triangle, Music } from "lucide-react";
import { Button } from "@/components/app/Button";
import {
  Card,
  CardTopRow,
  CardBadge,
  CardBody,
  type CardArt,
} from "@/components/app/Card";
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
  "Qwen",
  "Cohere", // unknown provider — exercises the --provider-default-* fallback
];

const AWARD_DEMO: {
  art: CardArt;
  color: string;
  icon: typeof Trophy;
  category: string;
  title: string;
  meta: string;
  date: string;
}[] = [
  {
    art: "contours",
    color: "var(--chart-5)",
    icon: Trophy,
    category: "Winner",
    title: "Media UX Award 2018-19",
    meta: "Toronto, Canada",
    date: "12 Oct 2019",
  },
  {
    art: "dots-flow",
    color: "var(--chart-2)",
    icon: Star,
    category: "Gold Winner",
    title: "Design Award 2018-19",
    meta: "United States",
    date: "28 Dec 2019",
  },
  {
    art: "chevron",
    color: "var(--chart-3)",
    icon: Gem,
    category: "Asia Pacific",
    title: "Yellow Dot Award 2019-20",
    meta: "United Nation",
    date: "28 Nov 2019",
  },
  {
    art: "dots",
    color: "var(--chart-1)",
    icon: Play,
    category: "Runner up",
    title: "Best Design 2019-20",
    meta: "North America",
    date: "28 Nov 2019",
  },
  {
    art: "stripes",
    color: "var(--chart-3)",
    icon: Triangle,
    category: "Silver Winner",
    title: "UX India Award 2020-21",
    meta: "Hyderabad, India",
    date: "30 Dec 2019",
  },
  {
    art: "dashes",
    color: "var(--chart-4)",
    icon: Music,
    category: "Winner",
    title: "Best Music Album 2018-19",
    meta: "Mumbai, India",
    date: "13 Aug 2019",
  },
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

      <Section title="Card — plain">
        <Card className="w-64">
          <p className="type-title">Plain card</p>
          <p className="type-body text-muted-foreground">
            Neutral surface, no border, no art.
          </p>
        </Card>
      </Section>

      <Section title="Card — art variants">
        <div className="grid w-full min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
          {AWARD_DEMO.map(({ art, color, icon: Icon, category, title, meta, date }) => (
            <Card
              key={art}
              art={art}
              artColor={color}
              className="aspect-square min-w-0 min-h-[280px]"
            >
              <CardTopRow>
                <CardBadge style={{ background: color }}>
                  <Icon size={26} aria-hidden="true" />
                </CardBadge>
                <span className="type-small text-muted-foreground">{date}</span>
              </CardTopRow>
              <CardBody>
                <p className="type-small text-muted-foreground mb-3.5">
                  {category}
                </p>
                <h3 className="type-heading">{title}</h3>
              </CardBody>
              <p className="type-small text-muted-foreground">{meta}</p>
            </Card>
          ))}
        </div>
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
