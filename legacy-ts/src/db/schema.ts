import {
  boolean,
  index,
  integer,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
} from "drizzle-orm/pg-core";

/**
 * First-cut schema (owner: P2, with P1 for auth, keys, orders and webhooks).
 * Money is stored as integer cents. Raw agent keys and approval tokens are never stored,
 * only their hashes. Tier 2 tables (score_history, alerts, refunds, badges) are added later.
 */
const pk = () =>
  text("id")
    .primaryKey()
    .$defaultFn(() => crypto.randomUUID());
const createdAt = () => timestamp("created_at", { withTimezone: true }).notNull().defaultNow();

export const users = pgTable("users", {
  id: pk(),
  email: text("email").notNull().unique(),
  name: text("name"),
  createdAt: createdAt(),
});

export const stores = pgTable("stores", {
  id: pk(),
  name: text("name").notNull(),
  ownerId: text("owner_id").references(() => users.id),
  paypalClientId: text("paypal_client_id"),
  feedUrl: text("feed_url"),
  isDemo: boolean("is_demo").notNull().default(false),
  createdAt: createdAt(),
});

export const products = pgTable(
  "products",
  {
    id: pk(),
    storeId: text("store_id")
      .notNull()
      .references(() => stores.id),
    paypalProductId: text("paypal_product_id"),
    name: text("name").notNull(),
    description: text("description").notNull().default(""),
    priceCents: integer("price_cents"),
    priceText: text("price_text"),
    currency: text("currency").notNull().default("USD"),
    stock: integer("stock"),
    variants: jsonb("variants").notNull().default([]),
    shipping: jsonb("shipping"),
    returns: jsonb("returns"),
    sku: text("sku"),
    gtin: text("gtin"),
    images: jsonb("images").notNull().default([]),
    category: text("category"),
    homeUrl: text("home_url"),
    checkoutRequiresHuman: boolean("checkout_requires_human").notNull().default(false),
    sourceHash: text("source_hash").notNull(),
    createdAt: createdAt(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    index("products_store_idx").on(t.storeId),
    uniqueIndex("products_store_sku_uq").on(t.storeId, t.sku),
  ],
);

export const importJobs = pgTable("import_jobs", {
  id: pk(),
  storeId: text("store_id")
    .notNull()
    .references(() => stores.id),
  sourceType: text("source_type").notNull(), // csv | feed | paypal | demo
  status: text("status").notNull().default("PENDING"),
  /** invalid rows are reported with line numbers, never silently dropped */
  rowErrors: jsonb("row_errors").notNull().default([]),
  createdAt: createdAt(),
});

export const scanRuns = pgTable("scan_runs", {
  id: pk(),
  storeId: text("store_id")
    .notNull()
    .references(() => stores.id),
  productCount: integer("product_count").notNull().default(0),
  storeScore: integer("store_score"),
  startedAt: createdAt(),
  finishedAt: timestamp("finished_at", { withTimezone: true }),
});

export const auditResults = pgTable(
  "audit_results",
  {
    id: pk(),
    productId: text("product_id")
      .notNull()
      .references(() => products.id),
    runId: text("run_id")
      .notNull()
      .references(() => scanRuns.id),
    score: integer("score").notNull(),
    issues: jsonb("issues").notNull().default([]),
    rulePackVersion: text("rule_pack_version").notNull(),
    createdAt: createdAt(),
  },
  (t) => [index("audit_results_product_idx").on(t.productId)],
);

export const fixProposals = pgTable(
  "fix_proposals",
  {
    id: pk(),
    productId: text("product_id")
      .notNull()
      .references(() => products.id),
    field: text("field").notNull(),
    oldValue: jsonb("old_value"),
    newValue: jsonb("new_value"),
    status: text("status").notNull().default("PROPOSED"),
    /** FixEvidence: source field, snippet, method, confidence. Required before APPLIED. */
    evidence: jsonb("evidence"),
    createdAt: createdAt(),
  },
  (t) => [index("fix_proposals_product_idx").on(t.productId)],
);

export const fixVersions = pgTable(
  "fix_versions",
  {
    id: pk(),
    productId: text("product_id")
      .notNull()
      .references(() => products.id),
    version: integer("version").notNull(),
    values: jsonb("values").notNull(),
    author: text("author").notNull(),
    createdAt: createdAt(),
  },
  (t) => [uniqueIndex("fix_versions_product_version_uq").on(t.productId, t.version)],
);

export const policies = pgTable("policies", {
  id: pk(),
  storeId: text("store_id")
    .notNull()
    .unique()
    .references(() => stores.id),
  autoApproveLimitCents: integer("auto_approve_limit_cents").notNull(),
  hardLimitCents: integer("hard_limit_cents").notNull(),
  dailyCapCents: integer("daily_cap_cents").notNull(),
  maxQuantity: integer("max_quantity").notNull(),
  allowedCategories: jsonb("allowed_categories").notNull().default([]),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const agents = pgTable("agents", {
  id: pk(),
  storeId: text("store_id")
    .notNull()
    .references(() => stores.id),
  name: text("name").notNull(),
  createdAt: createdAt(),
});

export const agentKeys = pgTable("agent_keys", {
  id: pk(),
  agentId: text("agent_id")
    .notNull()
    .references(() => agents.id),
  /** hash of the raw key; the raw key is shown once and never stored */
  keyHash: text("key_hash").notNull().unique(),
  keyPrefix: text("key_prefix").notNull(),
  scopes: jsonb("scopes").notNull().default([]),
  limits: jsonb("limits").notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }),
  revokedAt: timestamp("revoked_at", { withTimezone: true }),
  createdAt: createdAt(),
});

export const agentUsage = pgTable(
  "agent_usage",
  {
    id: pk(),
    agentId: text("agent_id")
      .notNull()
      .references(() => agents.id),
    day: text("day").notNull(), // YYYY-MM-DD (UTC)
    spentCents: integer("spent_cents").notNull().default(0),
    requestCount: integer("request_count").notNull().default(0),
  },
  (t) => [uniqueIndex("agent_usage_agent_day_uq").on(t.agentId, t.day)],
);

/** Database-backed rate limiting; in-memory counters do not work across serverless instances. */
export const rateLimits = pgTable(
  "rate_limits",
  {
    id: pk(),
    bucket: text("bucket").notNull(), // e.g. "key:<keyId>" or "ip:<ip>"
    windowStart: timestamp("window_start", { withTimezone: true }).notNull(),
    count: integer("count").notNull().default(0),
  },
  (t) => [uniqueIndex("rate_limits_bucket_window_uq").on(t.bucket, t.windowStart)],
);

export const agentRuns = pgTable("agent_runs", {
  id: pk(),
  mode: text("mode").notNull(), // BEFORE | AFTER
  agentConfig: text("agent_config").notNull(),
  taskId: text("task_id").notNull(),
  steps: jsonb("steps").notNull().default([]),
  outcome: text("outcome").notNull(),
  failReason: text("fail_reason"),
  tokens: integer("tokens"),
  durationMs: integer("duration_ms"),
  createdAt: createdAt(),
});

export const benchmarkRuns = pgTable("benchmark_runs", {
  id: pk(),
  label: text("label").notNull(),
  isRecorded: boolean("is_recorded").notNull().default(false),
  createdAt: createdAt(),
});

export const benchmarkResults = pgTable(
  "benchmark_results",
  {
    id: pk(),
    benchmarkRunId: text("benchmark_run_id")
      .notNull()
      .references(() => benchmarkRuns.id),
    agentConfig: text("agent_config").notNull(),
    mode: text("mode").notNull(),
    taskId: text("task_id").notNull(),
    outcome: text("outcome").notNull(),
    stepCount: integer("step_count").notNull(),
  },
  (t) => [index("benchmark_results_run_idx").on(t.benchmarkRunId)],
);

export const orders = pgTable(
  "orders",
  {
    id: pk(),
    storeId: text("store_id")
      .notNull()
      .references(() => stores.id),
    agentId: text("agent_id")
      .notNull()
      .references(() => agents.id),
    runId: text("run_id"),
    paypalOrderId: text("paypal_order_id").unique(),
    /** one idempotency key never creates two PayPal orders */
    idempotencyKey: text("idempotency_key").notNull().unique(),
    amountCents: integer("amount_cents").notNull(),
    currency: text("currency").notNull().default("USD"),
    items: jsonb("items").notNull(),
    policyDecision: text("policy_decision").notNull(),
    policyReason: text("policy_reason").notNull(),
    status: text("status").notNull(),
    createdAt: createdAt(),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("orders_store_idx").on(t.storeId)],
);

export const approvalRequests = pgTable("approval_requests", {
  id: pk(),
  orderId: text("order_id")
    .notNull()
    .references(() => orders.id),
  /** signed, single-use token; only its hash is stored */
  tokenHash: text("token_hash").notNull().unique(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  status: text("status").notNull().default("PENDING"), // PENDING | APPROVED | REJECTED | EXPIRED
  usedAt: timestamp("used_at", { withTimezone: true }),
  createdAt: createdAt(),
});

export const webhookEvents = pgTable("webhook_events", {
  id: pk(),
  /** unique: makes webhook handling idempotent (duplicate, delayed and out-of-order safe) */
  paypalEventId: text("paypal_event_id").notNull().unique(),
  eventType: text("event_type").notNull(),
  payload: jsonb("payload").notNull(),
  receivedAt: timestamp("received_at", { withTimezone: true }).notNull().defaultNow(),
  processedAt: timestamp("processed_at", { withTimezone: true }),
});

export const auditLog = pgTable(
  "audit_log",
  {
    id: pk(),
    ts: timestamp("ts", { withTimezone: true }).notNull().defaultNow(),
    actor: text("actor").notNull(), // agent | seller | system
    action: text("action").notNull(),
    detail: jsonb("detail").notNull().default({}),
    requestId: text("request_id"),
  },
  (t) => [index("audit_log_ts_idx").on(t.ts)],
);
