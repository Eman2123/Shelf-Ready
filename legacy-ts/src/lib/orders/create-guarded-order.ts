import type { GuardedOrderRequest, GuardedOrderResult } from "@/lib/contracts";
import { verifyAgentKey } from "@/lib/keys";

/**
 * STUB (owner: P1). Real flow: verify key -> build draft from the DB (never from agent-supplied
 * prices) -> evaluatePolicy -> create PayPal order with intent AUTHORIZE and a PayPal-Request-Id ->
 * capture only after ALLOW or seller approval. The stub never calls PayPal.
 */
export async function createGuardedOrder(req: GuardedOrderRequest): Promise<GuardedOrderResult> {
  const verification = await verifyAgentKey(req.agentKey);
  if (!verification.ok) {
    return {
      orderId: "stub-denied",
      status: "DENIED",
      paypalOrderId: null,
      decision: { decision: "DENY", reason: verification.reason },
      approvalUrl: null,
    };
  }
  return {
    orderId: "stub-order",
    status: "NEEDS_APPROVAL",
    paypalOrderId: null,
    decision: { decision: "NEEDS_APPROVAL", reason: "STUB_NOT_IMPLEMENTED" },
    approvalUrl: null,
  };
}
