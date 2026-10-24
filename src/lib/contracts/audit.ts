import { z } from "zod";
import { Id } from "./common";

export const Severity = z.enum(["CRITICAL", "HIGH", "MEDIUM", "LOW"]);

/** Stable issue codes. Add new codes at the end; never rename an existing one. */
export const IssueCode = z.enum([
  "PRICE_AMBIGUOUS",
  "PRICE_MISSING",
  "STOCK_MISSING",
  "VARIANTS_NOT_MACHINE_READABLE",
  "SHIPPING_MISSING",
  "RETURNS_MISSING",
  "DESCRIPTION_VAGUE",
  "IDENTIFIER_MISSING",
  "IMAGE_ALT_MISSING",
  "CHECKOUT_REQUIRES_HUMAN",
]);

/** How a fix can be produced. SELLER_INPUT means the data is not in the source. */
export const FixType = z.enum(["RULE_FILL", "AI_EXTRACT", "SELLER_INPUT", "STRUCTURE"]);

export const IssueSchema = z.object({
  code: IssueCode,
  severity: Severity,
  field: z.string(),
  message: z.string(),
  /** plain-language reason shown in the UI ("explain why") */
  why: z.string(),
  fixType: FixType,
  /** points lost in the readiness score because of this issue */
  pointsLost: z.number().int().nonnegative(),
});

export const AuditResultSchema = z.object({
  productId: Id,
  runId: Id,
  /** 0-100 */
  score: z.number().int().min(0).max(100),
  issues: z.array(IssueSchema),
  /** version of the rule pack that produced this result, for reproducibility */
  rulePackVersion: z.string(),
});

export type Severity = z.infer<typeof Severity>;
export type IssueCode = z.infer<typeof IssueCode>;
export type FixType = z.infer<typeof FixType>;
export type Issue = z.infer<typeof IssueSchema>;
export type AuditResult = z.infer<typeof AuditResultSchema>;

/** Score weights from the PRD (total 100). The audit engine must use these. */
export const SCORE_WEIGHTS = {
  price: 20,
  stock: 15,
  variants: 15,
  shipping: 15,
  returns: 10,
  description: 10,
  identifiers: 5,
  imageAlt: 5,
  checkoutPath: 5,
} as const;
