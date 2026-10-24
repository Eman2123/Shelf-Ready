import { z } from "zod";
import { IsoDateTime, Id } from "./common";

export const FixMethod = z.enum(["RULE", "AI_EXTRACT", "SELLER_INPUT"]);

export const FixStatus = z.enum([
  "PROPOSED",
  "NEEDS_SELLER_INPUT",
  "APPROVED",
  "APPLIED",
  "REJECTED",
]);

/**
 * Provenance for one proposed value. Hard rule (tested): no APPLIED value may exist
 * without evidence, and AI_EXTRACT may only quote text that exists in the source.
 */
export const FixEvidenceSchema = z.object({
  sourceField: z.string(),
  /** exact snippet from the source the value was derived from; empty for SELLER_INPUT */
  sourceSnippet: z.string(),
  method: FixMethod,
  /** 0..1 */
  confidence: z.number().min(0).max(1),
});

export const FixProposalSchema = z.object({
  id: Id,
  productId: Id,
  field: z.string(),
  oldValue: z.unknown(),
  /** null while status is NEEDS_SELLER_INPUT */
  newValue: z.unknown(),
  status: FixStatus,
  evidence: FixEvidenceSchema.nullable(),
});

export const FixVersionSchema = z.object({
  productId: Id,
  version: z.number().int().positive(),
  /** full snapshot of the product values at this version */
  values: z.record(z.string(), z.unknown()),
  author: z.enum(["agent", "seller", "system"]),
  createdAt: IsoDateTime,
});

export type FixMethod = z.infer<typeof FixMethod>;
export type FixStatus = z.infer<typeof FixStatus>;
export type FixEvidence = z.infer<typeof FixEvidenceSchema>;
export type FixProposal = z.infer<typeof FixProposalSchema>;
export type FixVersion = z.infer<typeof FixVersionSchema>;
