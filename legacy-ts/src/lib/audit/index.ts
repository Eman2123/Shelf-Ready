import type { Issue, Product } from "@/lib/contracts";

/**
 * Owner: P2. Versioned rule packs plus an AI rubric (cached by content hash).
 * Every rule returns one Issue (with code, severity, why and fix type) or null.
 */
export const RULE_PACK_VERSION = "2026.10.0";

export interface AuditRule {
  id: string;
  check(product: Product): Issue | null;
}
