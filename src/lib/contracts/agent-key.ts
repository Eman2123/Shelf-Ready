import { z } from "zod";
import { Cents, Id, IsoDateTime } from "./common";

export const KeyScope = z.enum(["read", "quote", "order"]);

export const KeyLimitsSchema = z.object({
  perOrderMaxCents: Cents,
  perDayBudgetCents: Cents,
  requestsPerMinute: z.number().int().positive(),
  allowedCategories: z.array(z.string()),
  expiresAt: IsoDateTime.nullable(),
});

export const VerifiedAgentSchema = z.object({
  agentId: Id,
  keyId: Id,
  storeId: Id,
  scopes: z.array(KeyScope),
  limits: KeyLimitsSchema,
});

export const KeyFailureReason = z.enum([
  "KEY_UNKNOWN",
  "KEY_REVOKED",
  "KEY_EXPIRED",
  "KEY_SCOPE_MISSING",
  "RATE_LIMITED",
  "OVER_AGENT_BUDGET",
  "OVER_PER_ORDER_MAX",
]);

/** Result of verifying a raw key string. A revoked key must fail on the very next request. */
export const KeyVerificationSchema = z.discriminatedUnion("ok", [
  z.object({ ok: z.literal(true), agent: VerifiedAgentSchema }),
  z.object({ ok: z.literal(false), reason: KeyFailureReason }),
]);

export type KeyScope = z.infer<typeof KeyScope>;
export type KeyLimits = z.infer<typeof KeyLimitsSchema>;
export type VerifiedAgent = z.infer<typeof VerifiedAgentSchema>;
export type KeyFailureReason = z.infer<typeof KeyFailureReason>;
export type KeyVerification = z.infer<typeof KeyVerificationSchema>;
