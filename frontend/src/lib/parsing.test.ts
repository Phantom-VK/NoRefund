import { describe, expect, it } from "vitest";
import { hasSupportedExtension } from "./parsing";

describe("hasSupportedExtension", () => {
  it("accepts a supported extension", () => {
    expect(hasSupportedExtension("report.pdf")).toBe(true);
  });

  it("is case-insensitive", () => {
    expect(hasSupportedExtension("REPORT.PDF")).toBe(true);
  });

  it("rejects an unsupported extension", () => {
    expect(hasSupportedExtension("archive.zip")).toBe(false);
  });

  it("rejects a bare directory name with no extension", () => {
    expect(hasSupportedExtension("some-folder")).toBe(false);
  });
});
