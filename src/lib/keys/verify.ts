import type { KeyVerification } from "@/lib/contracts";

/**
 * STUB (owner: P1). The real version hashes the key, looks it up, checks revoked/expiry/scope and
 * rate and budget limits, and must fail on the very next request after a kill switch.
 * The stub accepts exactly one development key and never in production.
 */
export async function verifyAgentKey(rawKey: string): Promise<KeyVerification> {
  if (process.env.NODE_ENV === "production" || rawKey !== "dev-demo-key") {
    return { ok: false, reason: "KEY_UNKNOWN" };
  }
  return {
    ok: true,
    agent: {
      agentId: "agent_dev",
      keyId: "key_dev",
      storeId: "store_demo",
      scopes: ["read", "quote", "order"],
      limits: {
        perOrderMaxCents: 20000,
        perDayBudgetCents: 50000,
        requestsPerMinute: 60,
        allowedCategories: ["apparel", "accessories", "kitchen"],
        expiresAt: null,
      },
    },
  };
}
