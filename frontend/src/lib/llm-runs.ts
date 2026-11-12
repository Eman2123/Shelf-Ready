import { z } from "zod";
import raw from "@/lib/fixtures/recorded-llm-runs.json";
import { recorded } from "@/lib/recorded";

/**
 * Real language-model runs (backend/app/scripts/record_llm_runs.py, file backend/data/benchmark/
 * llm_runs.json, copied here unchanged). They are kept apart from the scripted runs: different
 * file, different run ids (run_<task>_llm_<n>), and they are never mixed into the scripted totals.
 */
const Row = z.object({
  replica: z.number().int(),
  unsafe_action: z.boolean(),
  final: z.record(z.string(), z.unknown()),
  run: z.object({
    id: z.string(),
    task_id: z.string(),
    mode: z.enum(["BEFORE", "AFTER"]),
    outcome: z.string(),
    fail_reason: z.string().nullable(),
    duration_ms: z.number(),
    agent_config: z.string(),
    steps: z.array(z.object({ tool: z.string(), ok: z.boolean() }).passthrough()),
  }),
});

const File = z.object({
  k: z.number().int(),
  label: z.string(),
  provider: z.string(),
  recorded_at: z.string(),
  requested_model: z.string(),
  temperature: z.number(),
  runs: z.array(Row),
});

export const llm = File.parse(raw);

export type LlmRow = {
  id: string;
  taskId: string;
  title: string;
  expected: string;
  got: string;
  ok: boolean;
  unsafe: boolean;
  steps: number;
  tools: string;
  seconds: number;
  raw: unknown;
};

export function llmRows(): LlmRow[] {
  const byId = new Map(recorded.tasks.map((t) => [t.id, t]));
  return llm.runs
    .map((r) => {
      const task = byId.get(r.run.task_id);
      return {
        id: r.run.id,
        taskId: r.run.task_id,
        title: task?.title ?? r.run.task_id,
        expected: task?.expected ?? "?",
        got: String(r.final.kind ?? "?"),
        ok: r.run.outcome === "SUCCESS",
        unsafe: r.unsafe_action,
        steps: r.run.steps.length,
        tools: r.run.steps.map((s) => s.tool).join(" → "),
        seconds: r.run.duration_ms / 1000,
        raw: r,
      };
    })
    .sort((a, b) => a.taskId.localeCompare(b.taskId, undefined, { numeric: true }));
}

export function llmSummary() {
  const rows = llmRows();
  return {
    total: rows.length,
    ok: rows.filter((r) => r.ok).length,
    unsafe: rows.filter((r) => r.unsafe).length,
    avgSteps: rows.reduce((s, r) => s + r.steps, 0) / Math.max(rows.length, 1),
    ids: rows.map((r) => r.id),
  };
}
