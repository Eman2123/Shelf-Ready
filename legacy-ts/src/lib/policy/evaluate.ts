import type { OrderDraft, PolicyResult, PolicyRules } from "@/lib/contracts";

/**
 * STUB (owner: P1). Replace with the real deterministic engine.
 * Safe by design: it can never return ALLOW, so nothing can be captured by accident while the
 * real engine does not exist. Product text and agent text must never influence this function.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function evaluatePolicy(rules: PolicyRules, draft: OrderDraft): PolicyResult {
  return {
    decision: "NEEDS_APPROVAL",
    reason: "STUB_NOT_IMPLEMENTED",
    detail: "evaluatePolicy is a stub; every order needs approval until P1 implements it.",
  };
}
