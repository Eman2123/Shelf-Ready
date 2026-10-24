import { describe, expect, it } from "vitest";
import {
  KeyVerificationSchema,
  PolicyResultSchema,
  ProductSchema,
  SCORE_WEIGHTS,
  STORE_TOOL_NAMES,
} from "@/lib/contracts";
import { benchmarkTasks } from "@/lib/benchmark/tasks";
import { demoPolicyRules, fixtureProducts } from "@/lib/fixtures/products";

describe("contracts", () => {
  it("score weights add up to 100", () => {
    const total = Object.values(SCORE_WEIGHTS).reduce((a, b) => a + b, 0);
    expect(total).toBe(100);
  });

  it("fixture products satisfy the Product contract", () => {
    for (const p of fixtureProducts) expect(() => ProductSchema.parse(p)).not.toThrow();
  });

  it("has exactly the four store MCP tools", () => {
    expect([...STORE_TOOL_NAMES]).toEqual([
      "search_products",
      "get_product",
      "get_policy",
      "create_order",
    ]);
  });

  it("benchmark has 10 unique tasks", () => {
    expect(benchmarkTasks).toHaveLength(10);
    expect(new Set(benchmarkTasks.map((t) => t.id)).size).toBe(10);
  });

  it("demo policy keeps the auto-approve limit below the hard limit", () => {
    expect(demoPolicyRules.autoApproveLimitCents).toBeLessThan(demoPolicyRules.hardLimitCents);
  });

  it("key verification and policy results validate their shapes", () => {
    expect(() => KeyVerificationSchema.parse({ ok: false, reason: "KEY_REVOKED" })).not.toThrow();
    expect(() =>
      PolicyResultSchema.parse({ decision: "DENY", reason: "OVER_MAX_QUANTITY" }),
    ).not.toThrow();
  });
});
