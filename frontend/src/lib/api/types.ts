/** Shapes returned by backend/app/api. Money is integer cents. */

export type OrderStatus =
  | "DENIED"
  | "NEEDS_APPROVAL"
  | "CREATED"
  | "AUTHORIZED"
  | "CAPTURED"
  | "VOIDED"
  | "REFUNDED"
  | "FAILED";

export type PolicyDecision = "ALLOW" | "NEEDS_APPROVAL" | "DENY";

export interface ApiOrder {
  order_id: string;
  status: OrderStatus;
  agent_id: string;
  key_id: string;
  currency: string;
  total_cents: number;
  items: { product_id: string; quantity: number; unit_price_cents: number }[];
  decision: { decision: PolicyDecision; reason: string; detail: string | null };
  paypal_order_id: string | null;
  authorization_id: string | null;
  capture_id: string | null;
  refund_id: string | null;
  approval_url: string | null;
  seller_approved: boolean;
  failure: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApiApproval {
  approval_id: string;
  order_id: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";
  reason: string;
  detail: string | null;
  created_at: string;
  expires_at: string;
  decided_at: string | null;
}

export interface ApiWebhookEvent {
  event_id: string;
  event_type: string;
  resource_id: string | null;
  outcome: string;
  received_at: string;
}

export interface ApiKey {
  key_id: string;
  agent_id: string;
  store_id: string;
  scopes: string[];
  limits: {
    per_order_max_cents: number;
    per_day_budget_cents: number;
    requests_per_minute: number;
    allowed_categories: string[];
    expires_at: string | null;
  };
  created_at: string;
  revoked_at: string | null;
}

export interface Health {
  status: string;
  environment: string;
  paypal: "connected" | "not-connected";
}

export interface CatalogSync {
  fetched: number;
  added: string[];
  updated: string[];
  skipped: string[];
}
