import type { FixProposal } from "@/lib/contracts";

/**
 * SAMPLE fix records for the Fix review screen (owner: B). Mirrors
 * backend/app/services/fixtures/red_rejection.py: one record per lane.
 * These are NOT results from a real run; the screen labels them SAMPLE.
 */
export const SAMPLE_PRODUCT = { id: "prod_tee", name: "Tidewell Classic Tee" };
export const SOURCE_FIELD = "description";
export const SOURCE_TEXT =
  "Soft tee, great for everyday. Comes in lots of colors and sizes! " +
  "Call us to confirm your size. Machine wash cold.";

export const sampleFixes: FixProposal[] = [
  {
    id: "fix_green_care",
    productId: "prod_tee",
    field: "care_instructions",
    oldValue: null,
    newValue: "Machine wash cold",
    status: "APPLIED",
    evidence: {
      sourceField: SOURCE_FIELD,
      sourceSnippet: "Machine wash cold.",
      method: "AI_EXTRACT",
      confidence: 0.97,
    },
  },
  {
    id: "fix_red_material",
    productId: "prod_tee",
    field: "material",
    oldValue: null,
    newValue: "100% organic cotton",
    status: "REJECTED",
    evidence: {
      sourceField: SOURCE_FIELD,
      sourceSnippet: "100% organic cotton",
      method: "AI_EXTRACT",
      confidence: 0.91,
    },
    rejectionReason: "Snippet '100% organic cotton' is not in the source text.",
  },
  {
    id: "fix_yellow_sizes",
    productId: "prod_tee",
    field: "variants",
    oldValue: [],
    newValue: null,
    status: "NEEDS_SELLER_INPUT",
    evidence: null,
  },
];
