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
    // tail_len = floor(maxChars / 3), so the filename must be short enough
    // relative to maxChars to survive whole — see gui/formatting.py:95-102,
    // which this ports verbatim (elideMiddle("...report.pdf", 20) would
    // truncate the tail to "rt.pdf" and cannot contain the full name).
    const path = "/very/very/long/path/to/report.pdf";
    expect(elideMiddle(path, 30)).toContain("report.pdf");
    expect(elideMiddle(path, 30).length).toBeLessThanOrEqual(30);
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
