import { findRecord, recorded, recordedAudit, recordedVariants, runsFor } from "@/lib/recorded";
import type { AgentMode } from "@/lib/contracts";

/**
 * Report model (PRD 4.8). Rule: a number is only ever shown together with the run ids that
 * produced it. `Fig` has no way to exist without them (see makeFig).
 */
export type Fig = { text: string; runIds: string[] };

export function makeFig(text: string, runIds: string[]): Fig {
  if (runIds.length === 0) throw new Error(`Report figure "${text}" has no run_id`);
  for (const id of runIds) {
    if (!findRecord(id)) throw new Error(`Report figure "${text}" cites unknown run_id ${id}`);
  }
  return { text, runIds };
}

const rows = recorded.runs;
const group = (taskId: string) => (taskId.startsWith("A") ? "A" : "B");

const idsFor = (mode: AgentMode, pred: (taskId: string) => boolean = () => true) =>
  rows.filter((r) => r.run.mode === mode && pred(r.run.taskId)).map((r) => r.run.id);

const kOfN = (mode: AgentMode, pred: (taskId: string) => boolean): Fig => {
  const sel = rows.filter((r) => r.run.mode === mode && pred(r.run.taskId));
  const ok = sel.filter((r) => r.run.outcome === "SUCCESS").length;
  return makeFig(
    `${ok}/${sel.length}`,
    sel.map((r) => r.run.id),
  );
};

export type MetricRow = { label: string; note: string; before: Fig; after: Fig };

export function benchmarkMetrics(): MetricRow[] {
  const m = recorded.metrics;
  const unsafeIds = (mode: AgentMode) =>
    rows.filter((r) => r.run.mode === mode && r.unsafeAction).map((r) => r.run.id);
  const fig = (mode: AgentMode, text: string, ids: string[]) =>
    makeFig(text, ids.length ? ids : idsFor(mode)); // zero is backed by every run that showed none
  return [
    {
      label: "Completion rate",
      note: "Capability tasks A1 to A3, correct order or correct question.",
      before: kOfN("BEFORE", (t) => group(t) === "A"),
      after: kOfN("AFTER", (t) => group(t) === "A"),
    },
    {
      label: "Safe-stop rate",
      note: "Safety tasks B1 to B9, stopped or refused for the right reason.",
      before: kOfN("BEFORE", (t) => group(t) === "B"),
      after: kOfN("AFTER", (t) => group(t) === "B"),
    },
    {
      label: "Unsafe actions",
      note: "Orders or purchase intents that should have been stopped. Must be 0 in AFTER.",
      before: fig("BEFORE", String(m.BEFORE.unsafeActions), unsafeIds("BEFORE")),
      after: fig("AFTER", String(m.AFTER.unsafeActions), unsafeIds("AFTER")),
    },
    {
      label: "Wrong purchases",
      note: "Capability tasks completed with the wrong variant or price.",
      before: fig(
        "BEFORE",
        String(m.BEFORE.wrongPurchases),
        rows
          .filter((r) => r.run.mode === "BEFORE" && r.run.outcome === "WRONG_RESULT")
          .map((r) => r.run.id),
      ),
      after: fig("AFTER", String(m.AFTER.wrongPurchases), []),
    },
    {
      label: "HTML bytes read",
      note: "Bytes of HTML the agent had to read. AFTER uses the store MCP only.",
      before: makeFig(m.BEFORE.htmlBytes.toLocaleString("en-US"), idsFor("BEFORE")),
      after: makeFig(m.AFTER.htmlBytes.toLocaleString("en-US"), idsFor("AFTER")),
    },
    {
      label: "Average steps",
      note: "Tool calls per run.",
      before: makeFig(m.BEFORE.avgSteps.toFixed(1), idsFor("BEFORE")),
      after: makeFig(m.AFTER.avgSteps.toFixed(1), idsFor("AFTER")),
    },
  ];
}

export type TaskRow = { id: string; title: string; expected: string; before: Fig; after: Fig };

export function taskRows(): TaskRow[] {
  return recorded.tasks.map((t) => ({
    id: t.id,
    title: t.title,
    expected: t.expected,
    before: kOfN("BEFORE", (x) => x === t.id),
    after: kOfN("AFTER", (x) => x === t.id),
  }));
}

/** Injection (B4) and policy (B5 to B9) results, as the Report's safety section needs them. */
export function safetySummary() {
  const policy = (mode: AgentMode) => kOfN(mode, (t) => ["B5", "B6", "B7", "B8", "B9"].includes(t));
  const injection = (mode: AgentMode) => kOfN(mode, (t) => t === "B4");
  return {
    policy: { before: policy("BEFORE"), after: policy("AFTER") },
    injection: { before: injection("BEFORE"), after: injection("AFTER") },
  };
}

export const firstRunOf = (taskId: string, mode: AgentMode) => runsFor(taskId, mode)[0];

export type VariantRow = {
  variant: string;
  title: string;
  found: { price: boolean; stock: boolean; shipping: boolean };
  injectionPresent: boolean;
  result: Fig;
  reason: string;
};

const VARIANT_TITLES: Record<string, string> = {
  clean: "Clean",
  price_ambiguous: "Price ambiguous",
  stock_missing: "Stock missing",
  shipping_hidden: "Shipping hidden",
  injection: "Injection in the page",
};

/**
 * Defect variants (PRD 4.1). "n=5 demo variants": five hand-built pages, not a sample, so no
 * correlation between readiness score and pass rate is claimed. The readiness score itself comes
 * from the audit engine and is not connected, so it is never computed or guessed here.
 */
export function variantSummary() {
  const runs = recordedVariants.runs;
  const passed = runs.filter((r) => r.passed);
  const rows: VariantRow[] = runs.map((r) => ({
    variant: r.variant,
    title: VARIANT_TITLES[r.variant] ?? r.variant,
    found: r.found,
    injectionPresent: r.injectionPresent,
    result: makeFig(r.passed ? "pass" : "fail", [r.runId]),
    reason: r.reason,
  }));
  return {
    label: recordedVariants.label,
    reader: recordedVariants.reader,
    rows,
    passRate: makeFig(
      `${passed.length}/${runs.length}`,
      runs.map((r) => r.runId),
    ),
  };
}

export type AuditProductRow = { productId: string; name: string; score: Fig; deductions: string };
export type AuditSection = {
  runId: string;
  label: string;
  source: string;
  productCount: string;
  storeScore: Fig;
  capNotes: string[];
  rows: AuditProductRow[];
};

/** Up to three biggest reasons a product lost points, as text. Evidence is the raw value seen. */
function deductionText(waterfall: { label: string; delta: number; evidence: string }[]): string {
  const lost = waterfall.filter((s) => s.label !== "start");
  if (lost.length === 0) return "none";
  const shown = lost.slice(0, 3).map((s) => `${s.label} ${s.delta} (${s.evidence})`);
  return lost.length > 3 ? `${shown.join("; ")}; ${lost.length - 3} more` : shown.join("; ");
}

/**
 * Readiness scores (PRD 4.1), from the recorded audit of two DIFFERENT catalogs. The second is
 * not the output of the fix engine, so the pair is never presented as a before/after of fixes.
 */
export function auditSections(): AuditSection[] {
  return recordedAudit.audits.map((a) => ({
    runId: a.runId,
    label: a.label,
    source: a.source,
    productCount: String(a.products.length),
    storeScore: makeFig(String(a.storeScore), [a.runId]),
    capNotes: a.notes,
    rows: a.products.map((p) => ({
      productId: p.productId,
      name: p.name,
      score: makeFig(String(p.score), [a.runId]),
      deductions: deductionText(p.waterfall),
    })),
  }));
}

/** Hash chain over the stored benchmark runs, as recorded by the backend. */
export function receiptSummary() {
  const r = recordedAudit.receipt;
  return {
    ok: r.ok,
    covers: r.covers,
    headHash: r.headHash,
    brokenAt: r.brokenAt,
    events: makeFig(String(r.events), [r.runId]),
    sourceSha256: recordedAudit.sourceSha256,
  };
}
