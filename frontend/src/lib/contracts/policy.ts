import { z } from "zod";
import { Cents, CurrencyCode, Id } from "./common";

/**
 * Seller rules. Semantics (decided in PRD v3.1):
 *  - total <= autoApproveLimitCents            -> ALLOW (if every other rule passes)
 *  - autoApproveLimitCents < total <= hardLimitCents -> NEEDS_APPROVAL
 *  - total > hardLimitCents                    -> DENY
 * The AI never decides. Only code in src/lib/policy evaluates these.
 */
export const PolicyRulesSchema = z.object({
  autoApproveLimitCents: Cents,
  hardLimitCents: Cents,
  dailyCapCents: Cents,
  maxQuantity: z.number().int().positive(),
  allowedCategories: z.array(z.string()),
});

export const OrderItemDraftSchema = z.object({
  productId: Id,
  variantSku: z.string().nullable(),
  quantity: z.number().int().positive(),
  unitPriceCents: Cents,
  category: z.string().nullable(),
  inStock: z.boolean(),
});

export const OrderDraftSchema = z.object({
  storeId: Id,
  agentId: Id,
  currency: CurrencyCode,
  items: z.array(OrderItemDraftSchema).min(1),
  totalCents: Cents,
  /** what this agent has already spent today in this store, for the daily cap */
  spentTodayCents: Cents,
});

export const PolicyDecision = z.enum(["ALLOW", "NEEDS_APPROVAL", "DENY"]);

export const ReasonCode = z.enum([
  // policy rules
  "AUTO_APPROVED",
  "OVER_AUTO_APPROVE_LIMIT",
  "OVER_HARD_LIMIT",
  "OVER_DAILY_CAP",
  "OVER_MAX_QUANTITY",
  "CATEGORY_NOT_ALLOWED",
  "OUT_OF_STOCK",
  // agent key checks (same codes as KeyFailureReason in agent-key.ts)
  "KEY_UNKNOWN",
  "KEY_REVOKED",
  "KEY_EXPIRED",
  "KEY_SCOPE_MISSING",
  "RATE_LIMITED",
  "OVER_AGENT_BUDGET",
  "OVER_PER_ORDER_MAX",
  // placeholder used by stubs only
  "STUB_NOT_IMPLEMENTED",
]);

export const PolicyResultSchema = z.object({
  decision: PolicyDecision,
  reason: ReasonCode,
  detail: z.string().optional(),
});

export type PolicyRules = z.infer<typeof PolicyRulesSchema>;
export type OrderDraft = z.infer<typeof OrderDraftSchema>;
export type PolicyDecision = z.infer<typeof PolicyDecision>;
export type ReasonCode = z.infer<typeof ReasonCode>;
export type PolicyResult = z.infer<typeof PolicyResultSchema>;
