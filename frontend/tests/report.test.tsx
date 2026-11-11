import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Figure } from "@/components/report/figure";
import { ReportView } from "@/components/report/report-view";
import { findRecord, findRun, recorded, recordedAudit, recordedVariants } from "@/lib/recorded";
import {
  auditSections,
  benchmarkMetrics,
  makeFig,
  receiptSummary,
  safetySummary,
  taskRows,
  variantSummary,
} from "@/lib/report";

describe("report numbers", () => {
  it("a figure without a run_id cannot be built", () => {
    expect(() => makeFig("3/3", [])).toThrow(/no run_id/);
    expect(() => makeFig("3/3", ["run_does_not_exist"])).toThrow(/unknown run_id/);
    expect(() => renderToStaticMarkup(<Figure fig={{ text: "1", runIds: [] }} />)).toThrow();
  });

  it("every figure in the report model cites runs that exist", () => {
    const figs = [
      ...benchmarkMetrics().flatMap((m) => [m.before, m.after]),
      ...taskRows().flatMap((t) => [t.before, t.after]),
      safetySummary().policy.before,
      safetySummary().injection.after,
    ];
    for (const f of figs) {
      expect(f.runIds.length).toBeGreaterThan(0);
      for (const id of f.runIds) expect(findRun(id)).toBeDefined();
    }
  });

  it("the rendered report has no digit outside a figure or a marked static block", () => {
    let html = renderToStaticMarkup(<ReportView />);
    // drop every figure and every static block, then nothing numeric may remain
    html = html.replace(/<details data-figure[\s\S]*?<\/details>/g, "");
    html = html.replace(/<(\w+)[^>]*data-static[^>]*>[\s\S]*?<\/\1>/g, "");
    const text = html.replace(/<[^>]+>/g, " ").replace(/&[a-z#0-9]+;/g, " ");
    expect(text.match(/\d+/g) ?? []).toEqual([]);
  });

  it("every rendered figure lists its run ids", () => {
    const html = renderToStaticMarkup(<ReportView />);
    const figs = [...html.matchAll(/<details data-figure="true" data-run-ids="([^"]*)"/g)];
    expect(figs.length).toBeGreaterThan(20);
    for (const m of figs) expect(m[1].length).toBeGreaterThan(0);
  });

  it("states honestly that AFTER made no unsafe action and read no HTML", () => {
    const m = Object.fromEntries(benchmarkMetrics().map((r) => [r.label, r.after.text]));
    expect(m["Unsafe actions"]).toBe("0");
    expect(m["HTML bytes read"]).toBe("0");
  });

  it("defect variants: five runs, each figure cites a real run id, score not connected", () => {
    const v = variantSummary();
    expect(v.label).toBe("n=5 demo variants");
    expect(v.rows).toHaveLength(5);
    expect(v.reader).toMatch(/no LLM/);
    expect(v.passRate.runIds).toHaveLength(5);
    for (const id of v.passRate.runIds) expect(findRecord(id)).toBeDefined();
    for (const row of v.rows) expect(row.result.runIds).toHaveLength(1);
    const html = renderToStaticMarkup(<ReportView />);
    expect(html.match(/Not connected/g)!.length).toBeGreaterThanOrEqual(6);
  });

  it("variant pass count equals the recorded runs and the injection page is not obeyed", () => {
    const passed = recordedVariants.runs.filter((r) => r.passed).length;
    expect(variantSummary().passRate.text).toBe(`${passed}/5`);
    expect(recordedVariants.runs.every((r) => !r.obeyedInjection)).toBe(true);
  });

  it("makes no correlation claim between score and pass rate", () => {
    const html = renderToStaticMarkup(<ReportView />);
    expect(html).not.toMatch(/correlat(es|ed|ion) (with|between)/i);
    expect(html).toMatch(/no link between/);
  });

  it("audit scores and the receipt chain cite recorded runs and are not made up", () => {
    const sections = auditSections();
    expect(sections).toHaveLength(2);
    for (const a of sections) {
      expect(findRecord(a.storeScore.runIds[0])).toBeDefined();
      for (const r of a.rows) expect(findRecord(r.score.runIds[0])).toBeDefined();
    }
    const receipt = receiptSummary();
    expect(findRecord(receipt.events.runIds[0])).toBeDefined();
    expect(receipt.events.text).toBe(String(recorded.runs.length));
  });

  it("the report says the two audited catalogs are not a before and after of fixes", () => {
    const html = renderToStaticMarkup(<ReportView />);
    expect(html).toMatch(/not<\/strong> a before and after of fixes/);
    expect(html).toMatch(/Receipt chain: /);
  });

  it("shows the receipt chain as intact only when the recorded check passed", () => {
    expect(recordedAudit.receipt.ok).toBe(true);
    expect(renderToStaticMarkup(<ReportView />)).toMatch(/intact/);
  });
});
