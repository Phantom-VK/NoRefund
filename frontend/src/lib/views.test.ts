import { describe, expect, it } from "vitest";
import { VIEWS } from "./views";

describe("VIEWS", () => {
  it("has exactly six entries", () => {
    expect(VIEWS).toHaveLength(6);
  });

  it("groups into Tools (4) and Data (2)", () => {
    expect(VIEWS.filter((v) => v.section === "Tools")).toHaveLength(4);
    expect(VIEWS.filter((v) => v.section === "Data")).toHaveLength(2);
  });

  it("has unique ids", () => {
    const ids = VIEWS.map((v) => v.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("has shortcuts 1-6 with no gaps or duplicates", () => {
    const shortcuts = VIEWS.map((v) => v.shortcut).sort((a, b) => a - b);
    expect(shortcuts).toEqual([1, 2, 3, 4, 5, 6]);
  });
});
