import { describe, expect, it } from "vitest";
import { recorded, recordedAudit } from "@/lib/recorded";

describe("recorded audit snapshot", () => {
  it("has the two audited catalogs and the receipt chain", () => {
    expect(recordedAudit.audits.map((a) => a.runId)).toEqual([
      "audit_messy_csv",
      "audit_published_demo",
    ]);
    expect(recordedAudit.receipt.runId).toBe("receipt_benchmark_chain");
    expect(recordedAudit.sourceSha256).toMatch(/^[0-9a-f]{64}$/);
  });

  it("every product score equals the points of its passed checks, capped at 60 on a critical failure", () => {
    for (const a of recordedAudit.audits) {
      for (const p of a.products) {
        const raw = p.checks.reduce((sum, c) => sum + c.points, 0);
        expect(raw).toBe(p.rawScore);
        const criticalFailed = p.checks.some((c) => c.severity === "CRITICAL" && !c.passed);
        expect(p.score).toBe(criticalFailed ? Math.min(raw, 60) : raw);
      }
    }
  });

  it("every waterfall starts at 100 and adds up to the product score", () => {
    for (const a of recordedAudit.audits) {
      for (const p of a.products) {
        expect(p.waterfall[0]).toMatchObject({ label: "start", delta: 100 });
        expect(p.waterfall.reduce((sum, s) => sum + s.delta, 0)).toBe(p.score);
        for (const step of p.waterfall.slice(1)) expect(step.evidence.length).toBeGreaterThan(0);
      }
    }
  });

  it("the store score is the mean of its product scores unless a store cap applied", () => {
    for (const a of recordedAudit.audits) {
      const mean = a.products.reduce((sum, p) => sum + p.score, 0) / a.products.length;
      if (a.storeCapApplied) expect(a.storeScore).toBeLessThanOrEqual(60);
      else expect(Math.abs(a.storeScore - mean)).toBeLessThanOrEqual(0.5);
    }
  });

  it("every check carries the run id of its audit and a task link only when it failed", () => {
    for (const a of recordedAudit.audits) {
      for (const p of a.products) {
        for (const c of p.checks) {
          expect(c.runId).toBe(a.runId);
          if (c.passed) expect(c.taskLink).toBeNull();
        }
      }
    }
  });

  it("the chain event count equals the recorded benchmark runs", () => {
    expect(recordedAudit.receipt.events).toBe(recorded.runs.length);
    expect(recordedAudit.receipt.brokenAt).toBeNull();
  });
});
