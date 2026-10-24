import { z } from "zod";
import { Id } from "./common";

/** What a correct agent run ends with. Success = the expected outcome AND the policy was respected. */
export const ExpectedOutcome = z.enum([
  "ORDER_CREATED",
  "REPORTED_OUT_OF_STOCK",
  "STOPPED_FOR_APPROVAL",
  "DENIED_BY_POLICY",
  "REPORTED_CANNOT_SHIP",
  "INJECTION_IGNORED",
]);

export const BenchmarkTaskSchema = z.object({
  id: Id,
  title: z.string(),
  /** the exact task text given to the agent, identical in BEFORE and AFTER mode */
  prompt: z.string(),
  expected: ExpectedOutcome,
  /** what the check looks at, written down so the benchmark is honest and repeatable */
  successCriteria: z.string(),
});

export const AgentMode = z.enum(["BEFORE", "AFTER"]);

export const AgentStepSchema = z.object({
  index: z.number().int().nonnegative(),
  tool: z.string(),
  input: z.unknown(),
  output: z.unknown(),
  ok: z.boolean(),
});

export const AgentRunOutcome = z.enum(["SUCCESS", "FAILED", "WRONG_RESULT", "POLICY_VIOLATION"]);

export const AgentRunSchema = z.object({
  id: Id,
  mode: AgentMode,
  agentConfig: z.string(),
  taskId: Id,
  steps: z.array(AgentStepSchema),
  outcome: AgentRunOutcome,
  failReason: z.string().nullable(),
  durationMs: z.number().int().nonnegative(),
});

export type ExpectedOutcome = z.infer<typeof ExpectedOutcome>;
export type BenchmarkTask = z.infer<typeof BenchmarkTaskSchema>;
export type AgentMode = z.infer<typeof AgentMode>;
export type AgentStep = z.infer<typeof AgentStepSchema>;
export type AgentRunOutcome = z.infer<typeof AgentRunOutcome>;
export type AgentRun = z.infer<typeof AgentRunSchema>;
