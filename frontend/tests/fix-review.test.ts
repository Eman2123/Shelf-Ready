import { describe, expect, it } from "vitest";
import { laneOf, snippetSupported, splitAtSnippet, unsupportedCounter } from "@/lib/fix-review";
import { SOURCE_TEXT, sampleFixes } from "@/lib/fixtures/fix-records";

describe("fix review", () => {
  it("puts one sample fix in each lane", () => {
    expect(sampleFixes.map(laneOf)).toEqual(["green", "red", "yellow"]);
  });

  it("accepts only snippets that are in the source", () => {
    expect(snippetSupported(SOURCE_TEXT, "machine  WASH cold.")).toBe(true);
    expect(snippetSupported(SOURCE_TEXT, "100% organic cotton")).toBe(false);
    expect(snippetSupported(SOURCE_TEXT, "   ")).toBe(false);
  });

  it("shows 0 unsupported facts because the red proposal is blocked", () => {
    expect(unsupportedCounter(sampleFixes, SOURCE_TEXT)).toEqual({
      unsupported: 0,
      verified: 1,
      total: 1,
    });
  });

  it("counts an applied fix whose snippet is not in the source as unsupported", () => {
    const bad = sampleFixes.map((f) =>
      f.id === "fix_red_material" ? { ...f, status: "APPLIED" as const } : f,
    );
    expect(unsupportedCounter(bad, SOURCE_TEXT)).toEqual({ unsupported: 1, verified: 1, total: 2 });
  });

  it("splits the source around the snippet, or returns null when missing", () => {
    const r = splitAtSnippet(SOURCE_TEXT, "Machine wash cold.");
    expect(r?.match).toBe("Machine wash cold.");
    expect(r?.after).toBe("");
    expect(splitAtSnippet(SOURCE_TEXT, "100% organic cotton")).toBeNull();
  });
});
