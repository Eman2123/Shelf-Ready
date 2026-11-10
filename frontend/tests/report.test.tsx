import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Figure } from "@/components/report/figure";
import { ReportView } from "@/components/report/report-view";
import { findRun } from "@/lib/recorded";
import { benchmarkMetrics, makeFig, safetySummary, taskRows } from "@/lib/report";

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
});
