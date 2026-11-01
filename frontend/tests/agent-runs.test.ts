import { describe, expect, it } from "vitest";
import { AgentRunSchema, BenchmarkTaskSchema } from "@/lib/contracts";
import { sampleRuns, sampleTasks, totals } from "@/lib/fixtures/agent-runs";

describe("sample agent runs", () => {
  it("every task and run matches the contracts", () => {
    for (const t of sampleTasks) {
      expect(BenchmarkTaskSchema.safeParse(t).success).toBe(true);
      for (const mode of ["BEFORE", "AFTER"] as const) {
        const r = sampleRuns[t.id][mode];
        const { steps, ...rest } = r;
        const parsed = AgentRunSchema.safeParse({
          ...rest,
          steps: steps.map((s) => ({
            index: s.index,
            tool: s.tool,
            input: s.input,
            output: s.output,
            ok: s.ok,
          })),
        });
        expect(parsed.success, `${t.id} ${mode}`).toBe(true);
      }
    }
  });

  it("AFTER reads zero HTML bytes and BEFORE reads some", () => {
    for (const t of sampleTasks) {
      expect(totals(sampleRuns[t.id].AFTER).htmlBytes).toBe(0);
      expect(totals(sampleRuns[t.id].BEFORE).htmlBytes).toBeGreaterThan(0);
    }
  });

  it("BEFORE and AFTER use the same task id", () => {
    for (const t of sampleTasks) {
      expect(sampleRuns[t.id].BEFORE.taskId).toBe(t.id);
      expect(sampleRuns[t.id].AFTER.taskId).toBe(t.id);
    }
  });
});
