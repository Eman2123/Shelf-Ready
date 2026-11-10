import { z } from "zod";
import {
  AgentRunSchema,
  BenchmarkTaskSchema,
  type AgentMode,
  type AgentRun,
} from "@/lib/contracts";
import raw from "@/lib/fixtures/recorded-runs.json";
import rawVariants from "@/lib/fixtures/recorded-variants.json";

/**
 * Recorded benchmark runs (written by `make bench-run`, backend/app/scripts/run_benchmark.py).
 * The file is parsed against the contracts at load time, so a backend change that the UI does
 * not understand fails loudly instead of rendering wrong numbers.
 */
const Rate = z.object({ success: z.number().int(), runs: z.number().int() });

const ModeMetrics = z.object({
  completion: Rate,
  safeStop: Rate,
  unsafeActions: z.number().int(),
  wrongPurchases: z.number().int(),
  avgSteps: z.number(),
  htmlBytes: z.number().int(),
  perTask: z.record(
    z.string(),
    z.object({ success: z.number().int(), runs: z.number().int(), runIds: z.array(z.string()) }),
  ),
});

const RecordedSchema = z.object({
  sourceSha256: z.string(),
  k: z.number().int(),
  agentConfigs: z.array(z.string()),
  tasks: z.array(BenchmarkTaskSchema),
  metrics: z.object({ BEFORE: ModeMetrics, AFTER: ModeMetrics }),
  runs: z.array(
    z.object({
      run: AgentRunSchema,
      replica: z.number().int(),
      final: z.record(z.string(), z.unknown()),
      unsafeAction: z.boolean(),
    }),
  ),
});

export type RecordedRunRow = z.infer<typeof RecordedSchema>["runs"][number];
export const recorded = RecordedSchema.parse(raw);

export function runsFor(taskId: string, mode: AgentMode): RecordedRunRow[] {
  return recorded.runs
    .filter((r) => r.run.taskId === taskId && r.run.mode === mode)
    .sort((a, b) => a.replica - b.replica);
}

export function findRun(runId: string): RecordedRunRow | undefined {
  return recorded.runs.find((r) => r.run.id === runId);
}

export function totals(run: AgentRun) {
  return {
    toolCalls: run.steps.length,
    htmlBytes: run.steps.reduce((s, x) => s + x.htmlBytes, 0),
    durationMs: run.durationMs,
  };
}

/**
 * The five defect-variant runs (backend/app/services/benchmark/variants.py). A scripted page
 * reader with no LLM reads each hand-built page once. Label every result "n=5 demo variants".
 */
const VariantRunSchema = z.object({
  runId: z.string(),
  variant: z.string(),
  passed: z.boolean(),
  found: z.object({ price: z.boolean(), stock: z.boolean(), shipping: z.boolean() }),
  obeyedInjection: z.boolean(),
  injectionPresent: z.boolean(),
  reason: z.string(),
  htmlSha256: z.string(),
});

const RecordedVariantsSchema = z.object({
  sourceSha256: z.string(),
  label: z.string(),
  reader: z.string(),
  runs: z.array(VariantRunSchema),
});

export type VariantRun = z.infer<typeof VariantRunSchema>;
export const recordedVariants = RecordedVariantsSchema.parse(rawVariants);

export function findVariantRun(runId: string): VariantRun | undefined {
  return recordedVariants.runs.find((r) => r.runId === runId);
}

/** Any recorded run, benchmark or variant, by id. A report figure may cite either. */
export function findRecord(runId: string): RecordedRunRow | VariantRun | undefined {
  return findRun(runId) ?? findVariantRun(runId);
}
