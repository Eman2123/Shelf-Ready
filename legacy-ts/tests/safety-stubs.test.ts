import { describe, expect, it } from "vitest";
import { evaluatePolicy } from "@/lib/policy";
import { verifyAgentKey } from "@/lib/keys";
import { createGuardedOrder } from "@/lib/orders";
import { paypalBase } from "@/lib/paypal";
import { demoPolicyRules } from "@/lib/fixtures/products";

/**
 * These tests guard the foundation while the real money code does not exist yet.
 * P1 replaces the stubs; keep the sandbox-only and never-capture-by-accident checks.
 */
describe("safe stubs", () => {
  it("the policy stub can never ALLOW", () => {
    const result = evaluatePolicy(demoPolicyRules, {
      storeId: "store_demo",
      agentId: "agent_dev",
      currency: "USD",
      items: [
        {
          productId: "prod_tote",
          variantSku: null,
          quantity: 1,
          unitPriceCents: 100,
          category: "accessories",
          inStock: true,
        },
      ],
      totalCents: 100,
      spentTodayCents: 0,
    });
    expect(result.decision).not.toBe("ALLOW");
  });

  it("an unknown key is refused", async () => {
    const r = await verifyAgentKey("not-a-real-key");
    expect(r.ok).toBe(false);
  });

  it("an unknown key cannot create an order", async () => {
    const r = await createGuardedOrder({
      agentKey: "not-a-real-key",
      items: [{ productId: "prod_tote", quantity: 1 }],
      shipToCountry: "US",
      idempotencyKey: "test-key-0001",
    });
    expect(r.status).toBe("DENIED");
    expect(r.paypalOrderId).toBeNull();
  });

  it("refuses a non-sandbox PayPal base URL", () => {
    const prev = process.env.PAYPAL_API_BASE;
    process.env.PAYPAL_API_BASE = "https://api-m.paypal.com";
    expect(() => paypalBase()).toThrow(/sandbox-only/);
    if (prev === undefined) delete process.env.PAYPAL_API_BASE;
    else process.env.PAYPAL_API_BASE = prev;
  });
});
