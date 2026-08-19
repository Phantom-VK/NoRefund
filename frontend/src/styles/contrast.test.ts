import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// WCAG 2.1 relative luminance + contrast ratio, implemented inline so this
// test has no dependency on theme.css's own correctness to check itself.
function relativeLuminance(hex: string): number {
  const n = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(n.slice(i, i + 2), 16) / 255);
  const linearize = (c: number) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  const [lr, lg, lb] = [r, g, b].map(linearize);
  return 0.2126 * lr + 0.7152 * lg + 0.0722 * lb;
}

function contrastRatio(hexA: string, hexB: string): number {
  const la = relativeLuminance(hexA);
  const lb = relativeLuminance(hexB);
  const [lighter, darker] = la >= lb ? [la, lb] : [lb, la];
  return (lighter + 0.05) / (darker + 0.05);
}

// Strips @media (...) { ... } blocks (single level of nesting — theme.css
// never nests further) so the prefers-contrast overrides don't get folded
// into the base :root/.dark token values under test.
function stripMediaBlocks(css: string): string {
  let out = "";
  let i = 0;
  while (i < css.length) {
    const mediaStart = css.indexOf("@media", i);
    if (mediaStart === -1) {
      out += css.slice(i);
      break;
    }
    out += css.slice(i, mediaStart);
    const braceOpen = css.indexOf("{", mediaStart);
    let depth = 1;
    let j = braceOpen + 1;
    while (depth > 0 && j < css.length) {
      if (css[j] === "{") depth++;
      else if (css[j] === "}") depth--;
      j++;
    }
    i = j;
  }
  return out;
}

function extractVars(css: string, selector: string): Record<string, string> {
  const vars: Record<string, string> = {};
  const blockRe = new RegExp(
    selector.replace(".", "\\.") + "\\s*\\{([^}]*)\\}",
    "g",
  );
  let match: RegExpExecArray | null;
  while ((match = blockRe.exec(css))) {
    const propRe = /--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;/g;
    let propMatch: RegExpExecArray | null;
    while ((propMatch = propRe.exec(match[1]))) {
      vars[propMatch[1]] = propMatch[2];
    }
  }
  return vars;
}

const cssPath = join(dirname(fileURLToPath(import.meta.url)), "theme.css");
const rawCss = readFileSync(cssPath, "utf-8");
const strippedCss = stripMediaBlocks(rawCss);

const lightVars = extractVars(strippedCss, ":root");
const darkVars = { ...lightVars, ...extractVars(strippedCss, ".dark") };

const PROVIDERS = [
  "openai",
  "anthropic",
  "google",
  "deepseek",
  "meta",
  "mistral",
  "qwen",
  "default",
];

const PAIRS: [fg: string, bg: string][] = [
  ["primary-foreground", "primary"],
  ["foreground", "background"],
  ["card-foreground", "card"],
  ["muted-foreground", "card"],
  ["muted-foreground", "muted"],
  ["destructive-foreground", "destructive"],
  ["warning-foreground", "warning"],
  ...PROVIDERS.map(
    (p): [string, string] => [`provider-${p}-fg`, `provider-${p}-bg`],
  ),
];

describe.each([
  ["light", lightVars],
  ["dark", darkVars],
] as const)("contrast — %s theme", (themeName, vars) => {
  it.each(PAIRS)("%s on %s clears 4.5:1", (fgName, bgName) => {
    const fg = vars[fgName];
    const bg = vars[bgName];
    expect(fg, `--${fgName} not found in ${themeName} theme`).toBeDefined();
    expect(bg, `--${bgName} not found in ${themeName} theme`).toBeDefined();
    const ratio = contrastRatio(fg, bg);
    expect(
      ratio,
      `--${fgName} (${fg}) on --${bgName} (${bg}) in ${themeName} theme measured ${ratio.toFixed(2)}:1`,
    ).toBeGreaterThanOrEqual(4.5);
  });
});
