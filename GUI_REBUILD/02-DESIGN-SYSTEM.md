# Phase 02 — Design system: tokens, motion, typography, primitives

**Branch:** `feat/rebuild-02-design-system`
**Depends on:** Phase 01
**Prerequisite reading:** `00-OVERVIEW.md` §4 (Design Law)

> **REQUIRED SKILLS — load both before writing any code in this phase:**
> `apple-design` and `emil-design-eng`. This phase turns their rules into the
> tokens and primitives every later phase consumes. Getting it wrong here means
> every view inherits the mistake.

**Goal:** A complete, accessible, theme-aware design system with the motion
vocabulary baked in — so later phases compose primitives instead of inventing
styling.

**Out of scope:** any NoRefund screen, any bridge call, any business data. This
phase ships a component gallery, not a feature.

---

## Files

- Copy in: `frontend/src/components/ui/*` (from the Figma Make export)
- Create: `frontend/src/styles/theme.css`, `motion.css`, `typography.css`
- Create: `frontend/src/lib/cn.ts`, `frontend/src/lib/format.ts`
- Create: `frontend/src/hooks/useTheme.ts`, `frontend/src/hooks/useReducedMotion.ts`
- Create: `frontend/src/components/app/` — `Button.tsx`, `Card.tsx`,
  `StatPill.tsx`, `ContextBar.tsx`, `ProviderBadge.tsx`, `EmptyState.tsx`,
  `Spinner.tsx`, `SectionLabel.tsx`
- Create: `frontend/src/views/Gallery.tsx` (dev-only proof surface)
- Create: `frontend/src/lib/format.test.ts`
- Modify: `frontend/src/App.tsx`, `frontend/src/styles/index.css`,
  `frontend/package.json`

## Interfaces produced

```ts
// lib/cn.ts
export function cn(...inputs: ClassValue[]): string

// lib/format.ts   — port of src/norefund/gui/formatting.py
export function fmtNum(n: number): string
export function fmtFloat(v: number | null, decimals?: number): string
export function fmtCost(v: number): string
export function fmtContextPct(pct: number | null): string
export function fmtContextWindow(n: number): string
export function fmtBytes(n: number | null): string
export function parseIntSafe(value: string): number | null   // null = invalid
export function elideMiddle(text: string, maxChars: number): string
export function modelLabel(m: ModelInfo): string
export type ContextLevel = "ok" | "warn" | "over"
export function contextLevel(pct: number | null): ContextLevel

// hooks/useTheme.ts
export type ThemeMode = "light" | "dark" | "system"
export function useTheme(): { mode: ThemeMode; resolved: "light" | "dark";
                              setMode: (m: ThemeMode) => void }

// hooks/useReducedMotion.ts
export function useReducedMotion(): boolean

// components/app/*  — see Task 5 for exact props
```

---

## Task 1: Port the design tokens, with the contrast defects fixed

**Source:** `NoRefund Desktop UI Design/src/styles/theme.css` (183 lines).
Copy it to `frontend/src/styles/theme.css`, then apply the corrections below.

**The Figma design ships a real accessibility defect that must not be ported.**
Measured with the WCAG 2.1 relative-luminance formula:

| Token pair | Design value | Contrast | Verdict |
| --- | --- | --- | --- |
| `--primary-foreground` on `--primary` (light) | `#ffffff` on `#00b894` | **2.54:1** | ✗ fails AA |
| `--primary-foreground` on `--primary` (dark) | `#0d1117` on `#00d4aa` | 9.91:1 | ✓ |

This is the app's most-clicked surface — Analyze, Compare, Download. Light mode
uses white-on-mint; dark mode already uses dark-on-mint and is correct.

- [x] **Step 1.1: Copy the file**

```bash
cp "NoRefund Desktop UI Design/src/styles/theme.css" frontend/src/styles/theme.css
```

- [x] **Step 1.2: Fix the light-mode primary pair**

In the `:root` block, change:

```css
  --primary-foreground: #ffffff;
```
to:
```css
  /* Dark ink on the mint fill: 7.47:1. Matches what dark mode already does.
     The alternative — darkening --primary to #00846b for 4.65:1 against white
     — was rejected because it shifts the brand colour between themes. */
  --primary-foreground: #0d1117;
```

- [x] **Step 1.3: Add the provider palette**

The Figma design has no provider tokens; `gui/theme.py:53-60` does. Append to
`theme.css`. Each `-fg` value is the lightest tint of the brand colour that
still clears 4.5:1 against its own `-bg`, computed per theme.

```css
:root {
  --provider-openai-bg: #e0f3ee;    --provider-openai-fg: #0c7a5f;
  --provider-anthropic-bg: #f9f3ed; --provider-anthropic-fg: #7f6245;
  --provider-google-bg: #e6effe;    --provider-google-fg: #356ac3;
  --provider-deepseek-bg: #eaeaf3;  --provider-deepseek-fg: #5b5ea6;
  --provider-meta-bg: #dfebfb;      --provider-meta-fg: #0663d6;
  --provider-mistral-bg: #feede7;   --provider-mistral-fg: #af502f;
  --provider-default-bg: #f0f1f2;   --provider-default-fg: #686f76;

  --warning: #f59e0b;
  --warning-foreground: #111318;
}

.dark {
  --provider-openai-bg: #1a3838;    --provider-openai-fg: #34b192;
  --provider-anthropic-bg: #3d3836; --provider-anthropic-fg: #d4a373;
  --provider-google-bg: #23324e;    --provider-google-fg: #689df6;
  --provider-deepseek-bg: #272b40;  --provider-deepseek-fg: #9496c5;
  --provider-meta-bg: #182d4a;      --provider-meta-fg: #5195ea;
  --provider-mistral-bg: #442f2e;   --provider-mistral-fg: #fa7a4c;
  --provider-default-bg: #30353e;   --provider-default-fg: #979fa8;

  --warning: #f59e0b;
  --warning-foreground: #111318;
}
```

- [x] **Step 1.4: Add the high-contrast override**

```css
@media (prefers-contrast: more) {
  :root {
    --border: rgba(0, 0, 0, 0.45);
    --muted-foreground: #4b5563;
  }
  .dark {
    --border: rgba(255, 255, 255, 0.45);
    --muted-foreground: #a8b0b8;
  }
}
```

- [x] **Step 1.5: Commit**

```bash
git add frontend/src/styles/theme.css
git commit -m "feat(design): port design tokens, fix light-mode primary contrast"
```

---

## Task 2: The motion stylesheet

Every rule here comes from `00-OVERVIEW.md` §4. This file is the single place
motion is defined; **no later phase may hand-write a `transition` with a literal
duration or cubic-bezier.** Use these variables.

- [x] **Step 2.1: Create `frontend/src/styles/motion.css`**

```css
:root {
  /* Custom curves. The CSS built-ins are too weak to read as intentional. */
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
  --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);

  /* ease-in is deliberately absent. It delays the first frame — the one the
     user is watching — so it reads as sluggish at any duration. */

  --dur-press: 120ms;    /* pointer-down feedback        */
  --dur-tooltip: 150ms;  /* tooltips, small popovers     */
  --dur-dropdown: 180ms; /* selects, dropdowns, menus    */
  --dur-modal: 240ms;    /* dialogs, drawers, sheets     */
  --dur-exit: 140ms;     /* exits are always faster      */
}

/* Pressable: responds on pointer-DOWN, not on click.
   Apple: "the moment lag appears, the feeling of directness falls off a
   cliff." :active fires on press, which is exactly what we want. */
.pressable {
  transition: transform var(--dur-press) var(--ease-out);
  will-change: transform;
}
.pressable:active {
  transform: scale(0.97);
}

/* Radix data-state entrances. Origin-aware: popovers scale from their
   trigger, never from their own centre. Modals are exempt and stay centred. */
.anim-popover {
  transform-origin: var(--radix-popper-transform-origin);
  transition:
    opacity var(--dur-dropdown) var(--ease-out),
    transform var(--dur-dropdown) var(--ease-out);
}
.anim-popover[data-state="closed"] {
  transition-duration: var(--dur-exit);
}
.anim-popover[data-state="open"] {
  opacity: 1;
  transform: scale(1);
}
.anim-popover[data-state="closed"] {
  opacity: 0;
  /* Never scale(0) — nothing in the real world appears from nothing. */
  transform: scale(0.96);
}

.anim-modal {
  transform-origin: center;
  transition:
    opacity var(--dur-modal) var(--ease-out),
    transform var(--dur-modal) var(--ease-out);
}
.anim-modal[data-state="open"] {
  opacity: 1;
  transform: scale(1);
}
.anim-modal[data-state="closed"] {
  opacity: 0;
  transform: scale(0.97);
  transition-duration: var(--dur-exit);
}

/* Hover is gated: touch devices fire hover on tap, causing false positives. */
@media (hover: hover) and (pointer: fine) {
  .hoverable {
    transition: background-color var(--dur-press) var(--ease-out);
  }
}

/* Stagger for lists that appear as a group. 40ms steps — long enough to read
   as a cascade, short enough not to feel slow. Decorative only: never gate
   interaction on a stagger finishing. */
.stagger > * {
  animation: rise-in 260ms var(--ease-out) backwards;
}
.stagger > *:nth-child(1)  { animation-delay: 0ms; }
.stagger > *:nth-child(2)  { animation-delay: 40ms; }
.stagger > *:nth-child(3)  { animation-delay: 80ms; }
.stagger > *:nth-child(4)  { animation-delay: 120ms; }
.stagger > *:nth-child(5)  { animation-delay: 160ms; }
.stagger > *:nth-child(n + 6) { animation-delay: 200ms; }

@keyframes rise-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* Reduced motion means gentler, not absent: opacity and colour survive
   because they aid comprehension; movement and scaling do not. */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 120ms !important;
  }
  .pressable:active { transform: none; }
  .anim-popover[data-state="closed"],
  .anim-modal[data-state="closed"] { transform: none; }
  .stagger > * { animation: none; }
}

@media (prefers-reduced-transparency: reduce) {
  .translucent {
    background: var(--card) !important;
    backdrop-filter: none !important;
  }
}
```

- [x] **Step 2.2: Create `frontend/src/styles/typography.css`**

Tracking is size-specific — a single global `letter-spacing` is wrong at one end
of the scale or the other. Leading is inverse to size.

```css
.type-display {
  font-size: 1.75rem;
  line-height: 1.1;
  letter-spacing: -0.022em;
  font-weight: 700;
}
.type-heading {
  font-size: 1.375rem;
  line-height: 1.2;
  letter-spacing: -0.018em;
  font-weight: 700;
}
.type-title {
  font-size: 1.0625rem;
  line-height: 1.35;
  letter-spacing: -0.01em;
  font-weight: 600;
}
.type-label {
  font-size: 0.9375rem;
  line-height: 1.45;
  letter-spacing: 0;
}
.type-body {
  font-size: 0.875rem;
  line-height: 1.5;
  letter-spacing: 0;
}
.type-small {
  font-size: 0.8125rem;
  line-height: 1.45;
  letter-spacing: 0.005em;
}
.type-micro {
  font-size: 0.75rem;
  line-height: 1.4;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  font-weight: 600;
}

/* Tabular figures everywhere a number can change in place, so digits do not
   jitter as values update. */
.tabular {
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";
}
```

- [x] **Step 2.3: Wire them up in `frontend/src/styles/index.css`**

Add directly after the `@import "tailwindcss";` line:

```css
@import "./theme.css";
@import "./motion.css";
@import "./typography.css";
```

- [x] **Step 2.4: Commit**

```bash
git add frontend/src/styles/
git commit -m "feat(design): add motion and typography systems"
```

---

## Task 3: Theme switching

Three states, matching the existing `Settings.theme` field (`"system" | "light"
| "dark"`, `core/settings.py`). Phase 03 persists it; here it is local state.

- [x] **Step 3.1: Create `frontend/src/hooks/useTheme.ts`**

```ts
import { useCallback, useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";

const STORAGE_KEY = "norefund.theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function resolve(mode: ThemeMode): "light" | "dark" {
  if (mode === "system") return systemPrefersDark() ? "dark" : "light";
  return mode;
}

export function useTheme() {
  const [mode, setModeState] = useState<ThemeMode>(
    () => (localStorage.getItem(STORAGE_KEY) as ThemeMode | null) ?? "system",
  );
  const [resolved, setResolved] = useState<"light" | "dark">(() => resolve(mode));

  useEffect(() => {
    const apply = () => {
      const next = resolve(mode);
      setResolved(next);
      document.documentElement.classList.toggle("dark", next === "dark");
    };
    apply();
    if (mode !== "system") return;
    // Only track the OS while following it.
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [mode]);

  const setMode = useCallback((next: ThemeMode) => {
    localStorage.setItem(STORAGE_KEY, next);
    setModeState(next);
  }, []);

  return { mode, resolved, setMode };
}
```

- [x] **Step 3.2: Create `frontend/src/hooks/useReducedMotion.ts`**

```ts
import { useEffect, useState } from "react";

/** For motion that CSS cannot express declaratively (e.g. JS-driven counts). */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}
```

- [x] **Step 3.3: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat(design): add theme and reduced-motion hooks"
```

---

## Task 4: Port the formatting layer (with tests)

`gui/formatting.py` is pure and already unit-tested in `tests/test_formatting.py`.
Port both. **One deliberate behaviour change:** `parse_int` currently returns a
default on invalid input, which is how the Tk app silently turned `abc` into
`$0.00` (`GUI_REVIEW.md` §4.3). The TS version returns `null` so callers must
handle invalid explicitly.

- [x] **Step 4.1: Add a test runner**

```bash
cd frontend && npm install -D vitest@2.1.8
```
Add to `frontend/package.json` scripts: `"test": "vitest run"`.

- [x] **Step 4.2: Write `frontend/src/lib/format.test.ts`**

```ts
import { describe, expect, it } from "vitest";
import {
  contextLevel, elideMiddle, fmtBytes, fmtContextPct, fmtContextWindow,
  fmtCost, fmtNum, parseIntSafe,
} from "./format";

describe("fmtCost", () => {
  it("uses 6dp under a cent so tiny costs are not all $0.00", () => {
    expect(fmtCost(0.000123)).toBe("$0.000123");
  });
  it("uses 2dp at or above a cent", () => {
    expect(fmtCost(12.5)).toBe("$12.50");
    expect(fmtCost(1234.5)).toBe("$1,234.50");
  });
});

describe("fmtContextWindow", () => {
  it("renders millions without a trailing .0", () => {
    expect(fmtContextWindow(1_000_000)).toBe("1M tokens");
    expect(fmtContextWindow(1_500_000)).toBe("1.5M tokens");
  });
  it("renders thousands", () => expect(fmtContextWindow(128_000)).toBe("128K tokens"));
  it("renders small counts verbatim", () =>
    expect(fmtContextWindow(512)).toBe("512 tokens"));
});

describe("fmtBytes", () => {
  it("renders bytes without decimals", () => expect(fmtBytes(512)).toBe("512 B"));
  it("renders larger units with one decimal", () =>
    expect(fmtBytes(1536)).toBe("1.5 KB"));
  it("renders an em dash for null", () => expect(fmtBytes(null)).toBe("—"));
});

describe("parseIntSafe", () => {
  it("strips thousands separators", () => expect(parseIntSafe("1,024")).toBe(1024));
  it("returns null for empty input", () => expect(parseIntSafe("  ")).toBeNull());
  it("returns null rather than silently coercing garbage to 0", () => {
    expect(parseIntSafe("abc")).toBeNull();
  });
  it("returns null for negatives — no token count is negative", () => {
    expect(parseIntSafe("-5")).toBeNull();
  });
});

describe("contextLevel", () => {
  it("is ok below 75%", () => expect(contextLevel(10)).toBe("ok"));
  it("warns from 75% to under 100%", () => expect(contextLevel(80)).toBe("warn"));
  it("is over at 100% and above", () => expect(contextLevel(100)).toBe("over"));
  it("treats null as ok", () => expect(contextLevel(null)).toBe("ok"));
});

describe("elideMiddle", () => {
  it("keeps the tail, which identifies the file", () => {
    expect(elideMiddle("/very/long/path/to/report.pdf", 20)).toContain("report.pdf");
    expect(elideMiddle("/very/long/path/to/report.pdf", 20).length).toBeLessThanOrEqual(20);
  });
  it("passes short text through untouched", () =>
    expect(elideMiddle("short.txt", 40)).toBe("short.txt"));
});

describe("fmtNum / fmtContextPct", () => {
  it("groups thousands", () => expect(fmtNum(1234567)).toBe("1,234,567"));
  it("shows one decimal for percentages", () =>
    expect(fmtContextPct(12.34)).toBe("12.3%"));
  it("shows an em dash for a null percentage", () =>
    expect(fmtContextPct(null)).toBe("—"));
});
```

- [x] **Step 4.3: Run it and watch it fail**

```bash
cd frontend && npm test
```
Expected: fails to resolve `./format`.

- [x] **Step 4.4: Create `frontend/src/lib/format.ts`**

```ts
import type { ModelInfo } from "./types";

export function fmtNum(n: number): string {
  return n.toLocaleString("en-US");
}

export function fmtFloat(v: number | null, decimals = 1): string {
  if (v === null) return "—";
  return v.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtCost(v: number): string {
  if (v < 0.01) return `$${v.toFixed(6)}`;
  return `$${v.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function fmtContextPct(pct: number | null): string {
  return pct === null ? "—" : `${pct.toFixed(1)}%`;
}

export function fmtContextWindow(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M tokens`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K tokens`;
  return `${n} tokens`;
}

export function fmtBytes(n: number | null): string {
  if (n === null) return "—";
  let value = n;
  const units = ["B", "KB", "MB", "GB"] as const;
  for (const unit of units) {
    if (value < 1024 || unit === "GB") {
      return unit === "B" ? `${Math.round(value)} B` : `${value.toFixed(1)} ${unit}`;
    }
    value /= 1024;
  }
  return `${value.toFixed(1)} GB`;
}

/** null means "not a usable number" — callers must show an error, not fall
 *  back to 0. The Python original silently defaulted, which hid bad input. */
export function parseIntSafe(value: string): number | null {
  const cleaned = value.replace(/,/g, "").trim();
  if (cleaned === "") return null;
  if (!/^\d+$/.test(cleaned)) return null;
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : null;
}

export function elideMiddle(text: string, maxChars: number): string {
  if (text.length <= maxChars || maxChars <= 1) return text;
  const tail = Math.max(1, Math.floor(maxChars / 3));
  const head = maxChars - tail - 1;
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}

export function modelLabel(m: ModelInfo): string {
  const base = `${m.display_name}  ·  ${m.provider}`;
  return m.tokenizer_is_approximate ? `${base}  (approx.)` : base;
}

export type ContextLevel = "ok" | "warn" | "over";

export function contextLevel(pct: number | null): ContextLevel {
  if (pct === null || pct < 75) return "ok";
  if (pct < 100) return "warn";
  return "over";
}
```

`ModelInfo` does not exist yet — Phase 03 creates `lib/types.ts`. For now add a
temporary stub at the top of `lib/types.ts`:

```ts
export interface ModelInfo {
  id: string;
  display_name: string;
  provider: string;
  tokenizer_is_approximate: boolean;
}
```
Phase 03 replaces this file wholesale with the full generated types.

- [x] **Step 4.5: Run the tests**

```bash
cd frontend && npm test
```
Expected: all passing.

- [x] **Step 4.6: Commit**

```bash
git add frontend/src/lib/ frontend/package.json
git commit -m "feat(design): port formatting helpers with explicit invalid-input handling"
```

---

## Task 5: Base primitives

- [x] **Step 5.1: Copy the Radix/shadcn UI kit**

```bash
mkdir -p frontend/src/components/ui
cp "NoRefund Desktop UI Design/src/app/components/ui/"*.tsx frontend/src/components/ui/
cp "NoRefund Desktop UI Design/src/app/components/ui/"*.ts  frontend/src/components/ui/
```

Then install only the Radix packages those files actually import:

```bash
cd frontend
node -e "const fs=require('fs');const s=new Set();for(const f of fs.readdirSync('src/components/ui')){for(const m of fs.readFileSync('src/components/ui/'+f,'utf8').matchAll(/from \"(@radix-ui\/[^\"]+)\"/g))s.add(m[1]);}console.log([...s].join(' '))"
```

Install the printed list, pinning each to the version in the Figma design's
`package.json`. Delete any file in `components/ui/` that nothing imports —
**do not ship 48 primitives to use 12.**

- [x] **Step 5.2: Create `frontend/src/lib/cn.ts`**

```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

- [x] **Step 5.3: Create the app primitives**

Each is a thin composition over the UI kit plus the motion classes. Exact prop
contracts — later phases depend on these signatures:

```ts
// Button.tsx
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;   // default "secondary"
  icon?: LucideIcon;
  loading?: boolean;         // shows Spinner, sets aria-busy, disables
}

// Card.tsx
interface CardProps { className?: string; children: React.ReactNode;
                      accent?: boolean }  // accent = left accent strip

// StatPill.tsx
interface StatPillProps { label: string; value: string; mono?: boolean }

// ContextBar.tsx
interface ContextBarProps { pct: number | null; className?: string;
                            forceColor?: string }

// ProviderBadge.tsx
interface ProviderBadgeProps { provider: string }

// EmptyState.tsx
interface EmptyStateProps { icon: LucideIcon; title: string;
                            description?: string; action?: React.ReactNode }

// Spinner.tsx
interface SpinnerProps { size?: number; className?: string }

// SectionLabel.tsx
interface SectionLabelProps { children: React.ReactNode; className?: string }
```

Binding requirements — these encode `00-OVERVIEW.md` §4 and fix real defects
found in the Tk build:

1. **`Button`** carries `className="pressable"`. `variant="danger"` has a
   destructive-tinted **rest** state, not just on hover (`GUI_REVIEW.md` §4.5 —
   the Tk danger button was indistinguishable from a neutral one until hovered).
   `loading` renders `Spinner` and sets `aria-busy`.
2. **`Card`** with `accent` renders a 3px `--primary` strip on the left edge and
   keeps the card surface `--card`. **Never recolour the whole card** — the Tk
   build filled the winning Compare row with `--primary`, which made its
   progress bar 1.00:1 against its own background and rendered failure icons in
   white (`GUI_REVIEW.md` §4.1).
3. **`ContextBar`** picks its colour from `contextLevel(pct)`: `ok` →
   `--primary`, `warn` → `--warning`, `over` → `--destructive`. It sets
   `role="progressbar"` with `aria-valuenow` / `aria-valuemin` / `aria-valuemax`.
4. **`ProviderBadge`** maps a provider name to the `--provider-*-bg` / `-fg`
   pair, falling back to `--provider-default-*` for unknown providers such as
   Qwen. Uses `.type-micro`.
5. **`EmptyState`** is centred, muted, and always names the next action.
6. **`Spinner`** uses a CSS `@keyframes` rotation. Under
   `prefers-reduced-motion` the global rule flattens it to near-static, so it
   must remain legible as a static ring — do not rely on the spin to communicate.
7. Every numeric value uses `.tabular` so digits do not jitter as they update.

- [x] **Step 5.4: Build a gallery — `frontend/src/views/Gallery.tsx`**

Render every primitive, every variant, and every state (default, hover, active,
disabled, loading, focus-visible) on one scrollable page. Include a
`ContextBar` at 10 / 80 / 120 percent and a `ProviderBadge` for each of OpenAI,
Anthropic, Google, DeepSeek, Meta, Mistral and Qwen.

Point `App.tsx` at `<Gallery />` for this phase only. Phase 04 replaces it.

- [x] **Step 5.5: Verify the gallery by eye**

```bash
cd frontend && npm run build && cd .. && python -m norefund.desktop.app
```

Check, and record the result in the PR body:
- Toggling the OS theme switches the app live while `mode === "system"`.
- Every button visibly scales on **press**, not on release.
- Tab reaches every control and the focus ring is clearly visible.
- With `prefers-reduced-motion: reduce` forced on, nothing translates or scales,
  but opacity and colour still change.
- No horizontal scrollbar appears on the page at any window width ≥1024px.

- [x] **Step 5.6: Commit**

```bash
git add frontend/src/components/ frontend/src/views/Gallery.tsx frontend/src/App.tsx
git commit -m "feat(design): add base primitives and a component gallery"
```

---

## Task 6: Contrast regression test

The contrast defects in `GUI_REVIEW.md` §4.2 shipped because nothing checked
them. Lock the fix in.

- [x] **Step 6.1: Create `frontend/src/styles/contrast.test.ts`**

Parse `theme.css`, extract every `:root` and `.dark` custom property, and assert
these pairs meet 4.5:1 in **both** themes:

| Foreground | Background |
| --- | --- |
| `--primary-foreground` | `--primary` |
| `--foreground` | `--background` |
| `--card-foreground` | `--card` |
| `--muted-foreground` | `--card` |
| `--muted-foreground` | `--muted` |
| `--destructive-foreground` | `--destructive` |
| `--warning-foreground` | `--warning` |
| `--provider-<n>-fg` | `--provider-<n>-bg` (all seven) |

Implement the WCAG 2.1 relative-luminance formula inline — no dependency. Fail
with a message naming the pair, the measured ratio and the theme.

> **Note:** `--muted-foreground` on `--muted` measures 4.01:1 (light) and 3.96:1
> (dark) with the current tokens — it **will fail**. That is intended: it is a
> real defect (`GUI_REVIEW.md` §4.2). Darken `--muted-foreground` to `#5c636e`
> (light) and lighten to `#8b939c` (dark) until the test passes, then re-check
> the other pairs that use it.

- [x] **Step 6.2: Run until green**

```bash
cd frontend && npm test
```
Expected: all passing, including every contrast pair.

- [x] **Step 6.3: Commit**

```bash
git add frontend/src/styles/
git commit -m "test(design): assert WCAG AA contrast for every token pair"
```

---

## Definition of Done

- [x] `npm run typecheck` → 0 errors
- [x] `npm test` → all green, including the contrast suite (49 passed)
- [x] `npm run build` → succeeds
- [x] `pytest` and `ruff check src/` → unchanged and green (267 passed, clean)
- [x] Gallery renders every primitive in both themes — verified in the real
      desktop window (screenshots), not just a browser: both themes, the
      light-mode Primary-button contrast fix, Card's accent strip, ContextBar
      clamping at 120%, and the Qwen provider fallback all confirmed visually.
- [ ] Theme follows the OS in `system` mode and switches live — **partially
      verified**. Initial resolution to the OS's current preference is
      confirmed twice (matched this machine's `prefer-dark` gsettings value on
      launch). Live switching while running is **not** confirmed: toggling
      `gsettings set org.gnome.desktop.interface color-scheme` on this
      dev machine did not propagate into WebKitGTK's `prefers-color-scheme`
      after several seconds' wait, screenshotted twice. `useTheme.ts` uses the
      standard `matchMedia(...).addEventListener("change", ...)` pattern, so
      this looks like a gap in this minimal window-manager environment (likely
      missing xdg-desktop-portal wiring) rather than a code defect, but that
      is inference, not verification — needs checking on a full desktop
      environment or Windows/macOS.
- [ ] Press feedback fires on pointer-down — **not verified**. No input-
      synthesis tool (`xdotool`, `ydotool`) is available in this environment
      and none could be installed without interactive sudo. `.pressable`'s
      `:active` selector is the correct CSS-level mechanism (fires on
      pointer-down per spec), but this needs a manual click to confirm.
- [ ] Full keyboard traversal with a visible focus ring — **not verified**,
      same tooling gap as above. Needs a manual Tab-through.
- [x] `prefers-reduced-motion` removes movement but keeps opacity/colour —
      verified by inspection: motion.css's reduced-motion block is scoped to
      `animation-duration`/`transition-duration`/explicit `transform: none`
      overrides, and never touches `opacity` or `background-color` rules.
- [x] No `components/ui/` file is present that nothing imports **across the
      whole plan** — pruned 48 → 16 based on a full read of phases 03-13 (not
      just this phase); see the Task 5 commit message for the file-by-file
      reasoning. Note the literal DoD wording is stronger than what Phase 02
      alone satisfies: only `button.tsx` and `utils.ts` are imported by code
      that exists *yet* — the other 14 are reserved for named needs in later
      phases (e.g. `checkbox.tsx` for 08-Compare's ModelChecklist,
      `dialog.tsx` for 04's Settings modal). That matches the plan's stated
      intent ("do not ship 48 primitives to use 12", i.e. use across the
      whole rebuild) rather than a stricter same-phase-only reading.

## PR description

```markdown
Phase 02 of the GUI rebuild (see GUI_REBUILD/02-DESIGN-SYSTEM.md).

Design system: tokens, motion, typography, and base primitives. No product
screens yet — the app renders a component gallery.

- Ports the Figma Make design tokens, fixing a real accessibility defect it
  carried: --primary-foreground was #ffffff on #00b894 in light mode (2.54:1,
  fails WCAG AA) on the app's most-clicked surface. Now #0d1117 at 7.47:1,
  matching what dark mode already did.
- Adds provider colour pairs computed to clear 4.5:1 in both themes, including
  a fallback pair for providers with no brand colour (Qwen).
- motion.css is the single source of easing and duration. ease-in is
  deliberately absent; nothing interactive exceeds 300ms; only transform and
  opacity animate; popovers scale from their trigger and modals from centre.
- Honours prefers-reduced-motion, prefers-reduced-transparency, prefers-contrast.
- Ports gui/formatting.py to TypeScript with one deliberate change: parseIntSafe
  returns null for invalid input instead of silently coercing to 0
  (GUI_REVIEW.md §4.3).
- Adds a contrast regression test over every token pair, so §4.2 cannot recur.

core/ untouched. gui/ untouched and still runnable.
```
