import { describe, expect, it } from "vitest";
import { recorded, runsFor, totals } from "@/lib/recorded";

describe("recorded benchmark runs", () => {
  it("has 12 tasks and k runs per task and mode", () => {
    expect(recorded.tasks).toHaveLength(12);
    for (const t of recorded.tasks) {
      expect(runsFor(t.id, "BEFORE")).toHaveLength(recorded.k);
      expect(runsFor(t.id, "AFTER")).toHaveLength(recorded.k);
    }
  });

  it("AFTER reads zero HTML bytes, BEFORE reads some", () => {
    for (const t of recorded.tasks) {
      for (const r of runsFor(t.id, "AFTER")) expect(totals(r.run).htmlBytes).toBe(0);
      for (const r of runsFor(t.id, "BEFORE")) expect(totals(r.run).htmlBytes).toBeGreaterThan(0);
    }
  });

  it("metrics match the runs they summarise", () => {
    for (const mode of ["BEFORE", "AFTER"] as const) {
      const m = recorded.metrics[mode];
      const rs = recorded.runs.filter((r) => r.run.mode === mode);
      expect(m.unsafeActions).toBe(rs.filter((r) => r.unsafeAction).length);
      expect(m.htmlBytes).toBe(rs.reduce((s, r) => s + totals(r.run).htmlBytes, 0));
      const ok = rs.filter((r) => r.run.outcome === "SUCCESS").length;
      expect(m.completion.success + m.safeStop.success).toBe(ok);
    }
  });

  it("AFTER makes zero unsafe actions", () => {
    expect(recorded.metrics.AFTER.unsafeActions).toBe(0);
  });

  it("tool traffic keeps its real snake_case keys", () => {
    const run = runsFor("A2", "AFTER")[0].run;
    const order = run.steps.find((s) => s.tool === "create_order");
    expect(JSON.stringify(order?.input)).toContain("quote_id");
  });
});
