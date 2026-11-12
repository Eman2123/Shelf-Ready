import Link from "next/link";
import { Code, H3, Ic, Note, Section, Table } from "@/components/docs/parts";
import { SiteFooter } from "@/components/shell/site-footer";
import { Icon } from "@/components/ui";
import { Logo } from "@/components/ui/logo";

export const metadata = {
  title: "Docs · ShelfReady",
  description:
    "How Shelf Ready works: architecture, agent interface, keys, policy, PayPal order lifecycle, webhooks, API, setup and deploy.",
};

const TOC = [
  ["overview", "Overview"],
  ["architecture", "Architecture"],
  ["quickstart", "Quick start"],
  ["config", "Configuration"],
  ["agent-interface", "Agent interface (MCP)"],
  ["keys", "Agent keys"],
  ["policy", "Policy rules"],
  ["lifecycle", "Order lifecycle"],
  ["webhooks", "Webhooks"],
  ["api", "REST API"],
  ["sandbox", "Test on the PayPal sandbox"],
  ["deploy", "Deploy"],
  ["security", "Security"],
  ["limits", "What is not built"],
  ["troubleshooting", "Troubleshooting"],
] as const;

const ARCH = `AI shopping agent
      |  MCP over HTTP: POST /mcp  (search_products, get_product, get_policy, create_order)
      v
 Store service ---- checks the agent key, then the price quote it handed out
      |
      v
 Policy engine ---- ALLOW / NEEDS_APPROVAL / DENY, decided by code only
      |
      v
 Order service ---- PayPal: create (AUTHORIZE) -> buyer approves -> authorize
      |             -> witness read-back -> capture   (or void / refund)
      v
 Postgres  <----    keys, spend, orders, approvals, webhook events, order log
      ^
 PayPal webhooks -> POST /api/webhooks/paypal  (signature verified by PayPal)

Seller dashboard (Next.js) -> REST API with X-Admin-Token`;

const MCP_CALL = `{
  "items": [
    { "product_id": "prod_mug", "variant_sku": "MUG-STD", "quantity": 2,
      "quote_id": "<quote_id from get_product>" }
  ],
  "ship_to_country": "US",
  "idempotency_key": "order-2026-11-12-0001",
  "agent_key": "srk_..."
}`;

const MCP_RESULT = `{
  "order_id": "ord_3f9c1a7e42b0",
  "status": "CREATED",
  "paypal_order_id": "5O190127TN364715T",
  "decision": { "decision": "ALLOW", "reason": "AUTO_APPROVED", "detail": null },
  "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=..."
}`;

export default function DocsPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-ink focus:p-3 focus:text-paper"
      >
        Skip to content
      </a>
      <header className="border-b-4 border-double border-ink">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <Logo />
          <nav aria-label="Site" className="flex items-center gap-6 text-sm font-semibold">
            <Link href="/" className="hover:underline">
              Home
            </Link>
            <Link
              href="/app"
              className="bg-ink px-4 py-2 font-extrabold uppercase tracking-wide text-paper hover:bg-signal"
            >
              Dashboard
            </Link>
          </nav>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-10 px-4 py-10 lg:grid-cols-[14rem_1fr]">
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <nav aria-label="On this page" className="border-2 border-ink p-4">
            <p className="flex items-center gap-2 font-mono text-xs font-bold uppercase text-mute">
              <Icon name="fix" size={16} /> On this page
            </p>
            <ol className="mt-3 space-y-1.5 text-sm font-semibold">
              {TOC.map(([id, label], i) => (
                <li key={id}>
                  <a href={`#${id}`} className="hover:underline">
                    <span className="mr-1.5 font-mono text-xs text-mute">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    {label}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
        </aside>

        <main id="main" tabIndex={-1} className="min-w-0 space-y-12">
          <div>
            <p className="font-mono text-xs font-bold uppercase text-signal">Documentation</p>
            <h1 className="mt-2 font-display text-5xl font-bold leading-none tracking-tight md:text-6xl">
              How Shelf Ready works
            </h1>
            <p className="mt-4 max-w-2xl text-lg">
              Everything about the project in one page: what runs where, how an agent order becomes
              a PayPal payment, which rules protect the seller, and how to run and deploy it. PayPal
              sandbox only. No real money moves.
            </p>
          </div>

          <Section id="overview" title="Overview">
            <p>
              Small shops publish prices like &ldquo;from $20&rdquo;, hide stock, and need a human
              at checkout. An AI shopping agent that reads such a page guesses, and a guess can
              become a wrong purchase. Shelf Ready has three parts:
            </p>
            <Table
              head={["Part", "What it does"]}
              rows={[
                [
                  <strong key="a">Agent-ready store</strong>,
                  "Exposes the catalog to agents through typed tools (MCP) with exact prices, stock and a price quote per variant.",
                ],
                [
                  <strong key="b">Guarded checkout</strong>,
                  "Every order goes through an agent key, a policy engine and PayPal authorize-then-capture. A seller approval queue handles larger orders.",
                ],
                [
                  <strong key="c">Before and after test</strong>,
                  "The same scripted buyer agent runs against the old page and the agent-ready store, and the recorded results are fingerprinted so anyone can re-check them.",
                ],
              ]}
            />
            <Note>
              The scripted baseline agents in the benchmark are not language models. The model-based
              runs are recorded separately and only when an API key is configured.
            </Note>
          </Section>

          <Section id="architecture" title="Architecture">
            <Code label="Data flow">{ARCH}</Code>
            <p>
              <strong>Rule that never changes:</strong> a language model never decides about money.
              The agent only asks. The key check, quote check, limits and approval are plain code,
              and PayPal is the system that moves funds.
            </p>
            <Table
              head={["Folder", "Contents"]}
              rows={[
                [
                  <Ic key="1">backend/app/services/mcp_store</Ic>,
                  "MCP tools and the store service",
                ],
                [
                  <Ic key="2">backend/app/services/policy</Ic>,
                  "Policy engine (ALLOW, NEEDS_APPROVAL, DENY)",
                ],
                [
                  <Ic key="3">backend/app/services/orders</Ic>,
                  "Guarded order flow, approvals, refunds",
                ],
                [
                  <Ic key="4">backend/app/services/paypal</Ic>,
                  "OAuth client, Orders v2, webhooks, catalog",
                ],
                [
                  <Ic key="5">backend/app/db</Ic>,
                  "SQLAlchemy models, repositories, Alembic migrations",
                ],
                [<Ic key="6">frontend/src</Ic>, "Landing page, docs and the seller dashboard"],
              ]}
            />
          </Section>

          <Section id="quickstart" title="Quick start">
            <H3>Backend (Python 3.12 or 3.13)</H3>
            <Code label="PowerShell">{`cd backend
py -3.12 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
python -m pytest -q          # expect: all tests pass
uvicorn app.main:app --port 8000`}</Code>
            <Note kind="warn">
              Python 3.14 has no ready-made wheels for some dependencies yet, so installing fails.
              Use 3.12 or 3.13. On macOS or Linux, activate with <Ic>source .venv/bin/activate</Ic>.
            </Note>
            <H3>Frontend (Node 20+)</H3>
            <Code label="Terminal">{`cd frontend
npm ci
npm run dev                  # http://localhost:3000`}</Code>
            <p>
              Open <Ic>/app/keys</Ic>, paste your <Ic>ADMIN_TOKEN</Ic> and create a key. Without a
              database URL the backend keeps everything in memory, so data resets on restart.
            </p>
          </Section>

          <Section id="config" title="Configuration">
            <p>
              The backend reads <Ic>backend/.env</Ic>, then the repo-root <Ic>.env</Ic> and{" "}
              <Ic>.env.local</Ic>. Variables already set in the shell or on the host always win.
              Never commit these files.
            </p>
            <Table
              head={["Variable", "Needed for", "Notes"]}
              rows={[
                [
                  <Ic key="1">ADMIN_TOKEN</Ic>,
                  "Keys, orders, approvals screens",
                  "You invent it. A long random string. Sent as the X-Admin-Token header.",
                ],
                [
                  <Ic key="2">PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET</Ic>,
                  "Any PayPal call",
                  "From a Sandbox app on developer.paypal.com. Without them orders end in ORDER_BACKEND_NOT_CONNECTED.",
                ],
                [
                  <Ic key="3">PAYPAL_WEBHOOK_ID</Ic>,
                  "Webhooks",
                  "Id of the webhook you register for your deployed URL. Missing means every webhook is rejected.",
                ],
                [
                  <Ic key="4">PAYPAL_API_BASE</Ic>,
                  "Optional",
                  "Defaults to https://api-m.sandbox.paypal.com.",
                ],
                [
                  <Ic key="5">DATABASE_URL</Ic>,
                  "Persistence",
                  "Postgres URL (Neon works). Empty means in-memory SQLite.",
                ],
                [
                  <Ic key="6">APP_URL</Ic>,
                  "CORS and PayPal return links",
                  "Your frontend URL, e.g. https://shelf-ready.vercel.app.",
                ],
                [
                  <Ic key="7">AI_PROVIDER + *_API_KEY + *_MODEL</Ic>,
                  "Recording model runs",
                  "aiml or gemini. Only used by the record_llm_runs script.",
                ],
                [
                  <Ic key="8">NEXT_PUBLIC_API_BASE_URL</Ic>,
                  "Frontend",
                  "The backend URL the browser calls.",
                ],
                [
                  <Ic key="9">NEXT_PUBLIC_DEMO_ADMIN_TOKEN</Ic>,
                  "Optional, judging",
                  "Pre-fills the admin token in the browser. Public by design: use a throwaway token on a sandbox-only deployment.",
                ],
              ]}
            />
          </Section>

          <Section id="agent-interface" title="Agent interface (MCP)">
            <p>
              Agents connect to <Ic>POST /mcp</Ic> (streamable HTTP). Prices are integer cents.
            </p>
            <Table
              head={["Tool", "Purpose"]}
              rows={[
                [
                  <Ic key="1">search_products</Ic>,
                  "Search by text, category and max price (cents).",
                ],
                [
                  <Ic key="2">get_product</Ic>,
                  "One product with typed variants, stock and a quote_id for each variant.",
                ],
                [
                  <Ic key="3">get_policy</Ic>,
                  "The seller's limits and allowed categories. Read before ordering.",
                ],
                [
                  <Ic key="4">create_order</Ic>,
                  "Create a guarded order. Needs the quote_id and an agent key.",
                ],
              ]}
            />
            <H3>create_order input and result</H3>
            <Code label="Input">{MCP_CALL}</Code>
            <Code label="Result">{MCP_RESULT}</Code>
            <p>
              The price is never taken from the request. The server reads it from the stored quote,
              so an agent cannot choose its own price. Error results are objects with an{" "}
              <Ic>error</Ic> code, for example <Ic>KEY_UNKNOWN</Ic>, <Ic>PRICE_CHANGED</Ic> or{" "}
              <Ic>ORDER_BACKEND_NOT_CONNECTED</Ic>.
            </p>
            <p>
              Discovery files: <Ic>/.well-known/agent-store.json</Ic> describes the store, and{" "}
              <Ic>/agent-ready/products/{"{id}"}/jsonld</Ic> returns schema.org JSON-LD for a
              product.
            </p>
          </Section>

          <Section id="keys" title="Agent keys">
            <ul className="list-disc space-y-1 pl-5">
              <li>
                One key per agent. The raw key (<Ic>srk_...</Ic>) is shown <strong>once</strong>;
                only its SHA-256 hash is stored.
              </li>
              <li>
                Scopes: <Ic>read</Ic>, <Ic>quote</Ic>, <Ic>order</Ic>. An order needs the{" "}
                <Ic>order</Ic> scope.
              </li>
              <li>
                Limits per key: per-order maximum, daily budget, requests per minute, allowed
                categories and an optional expiry.
              </li>
              <li>
                Revoking works on the agent&apos;s next request. Keys, revocations and daily spend
                are stored in the database and survive a restart.
              </li>
            </ul>
          </Section>

          <Section id="policy" title="Policy rules">
            <p>
              The seller&apos;s default policy: orders up to <strong>$50</strong> are approved
              automatically, anything above that needs the seller, and anything above{" "}
              <strong>$200</strong> is denied. Total spend per day is capped at{" "}
              <strong>$300</strong>. The agent&apos;s own key limits apply on top.
            </p>
            <Table
              head={["Reason code", "Decision", "Meaning"]}
              rows={[
                [<Ic key="1">AUTO_APPROVED</Ic>, "ALLOW", "Inside every limit."],
                [
                  <Ic key="2">OVER_AUTO_APPROVE_LIMIT</Ic>,
                  "NEEDS_APPROVAL",
                  "Above the auto-approve amount. Waits in the seller queue.",
                ],
                [
                  <Ic key="3">OVER_HARD_LIMIT</Ic>,
                  "DENY",
                  "Above the hard limit. PayPal is never called.",
                ],
                [<Ic key="4">OVER_DAILY_CAP</Ic>, "DENY", "Would exceed the store's daily cap."],
                [<Ic key="5">OVER_MAX_QUANTITY</Ic>, "DENY", "Too many units of one item."],
                [
                  <Ic key="6">CATEGORY_NOT_ALLOWED</Ic>,
                  "DENY",
                  "The key may not buy this category.",
                ],
                [<Ic key="7">OUT_OF_STOCK</Ic>, "DENY", "Not enough stock."],
                [
                  <Ic key="8">OVER_PER_ORDER_MAX / OVER_AGENT_BUDGET</Ic>,
                  "DENY",
                  "The key's own per-order or daily limit.",
                ],
                [
                  <Ic key="9">
                    KEY_UNKNOWN / KEY_REVOKED / KEY_EXPIRED / KEY_SCOPE_MISSING / RATE_LIMITED
                  </Ic>,
                  "DENY",
                  "Key checks.",
                ],
                [
                  <Ic key="10">PRICE_CHANGED / STOCK_CHANGED / QUOTE_EXPIRED</Ic>,
                  "DENY",
                  "The quote no longer matches the catalog. Ask for a new quote.",
                ],
              ]}
            />
          </Section>

          <Section id="lifecycle" title="Order lifecycle">
            <ol className="list-decimal space-y-2 pl-5">
              <li>
                <strong>Create.</strong> Key check, quote check, policy decision. A DENY stops here
                and PayPal is not called. Otherwise a PayPal order is created with intent{" "}
                <Ic>AUTHORIZE</Ic> and the buyer gets an <Ic>approval_url</Ic>.
              </li>
              <li>
                <strong>Buyer approves</strong> in PayPal. The webhook{" "}
                <Ic>CHECKOUT.ORDER.APPROVED</Ic> arrives and the store authorizes the payment. Funds
                are held, not taken.
              </li>
              <li>
                <strong>Decide.</strong> If the policy said ALLOW, or the seller already approved,
                the store continues. Otherwise it waits in the approval queue.
              </li>
              <li>
                <strong>Witness.</strong> The store reads the order back from PayPal and checks the
                order id, total, currency and authorization id against what it stored. A mismatch
                voids the authorization and marks the order FAILED.
              </li>
              <li>
                <strong>Capture.</strong> The authorization is captured for the stored amount, and
                the key&apos;s daily spend is updated.
              </li>
              <li>
                <strong>Reject or timeout.</strong> The authorization is voided and nothing is
                charged. Pending approvals expire after 24 hours.
              </li>
              <li>
                <strong>Refund.</strong> A captured order can be refunded from the dashboard.
              </li>
            </ol>
            <Table
              head={["Status", "Meaning"]}
              rows={[
                [<Ic key="1">DENIED</Ic>, "Stopped by a rule. No PayPal call."],
                [<Ic key="2">CREATED</Ic>, "PayPal order created, waiting for the buyer."],
                [
                  <Ic key="3">NEEDS_APPROVAL</Ic>,
                  "Created, and the seller must approve before capture.",
                ],
                [<Ic key="4">AUTHORIZED</Ic>, "Funds held by PayPal."],
                [<Ic key="5">CAPTURED</Ic>, "Money taken."],
                [<Ic key="6">VOIDED</Ic>, "Authorization released."],
                [<Ic key="7">REFUNDED</Ic>, "Captured, then refunded."],
                [
                  <Ic key="8">FAILED</Ic>,
                  "PayPal error or witness mismatch. The reason is stored.",
                ],
              ]}
            />
            <Note>
              Status only moves forward. Every PayPal write carries a request id derived from the
              order, and creating an order twice with the same <Ic>idempotency_key</Ic> returns the
              first order, so a retry can never create or charge twice.
            </Note>
          </Section>

          <Section id="webhooks" title="Webhooks">
            <p>
              PayPal calls <Ic>POST /api/webhooks/paypal</Ic>. The body is never trusted until
              PayPal&apos;s own verification API returns <Ic>SUCCESS</Ic> for the signature headers
              and <Ic>PAYPAL_WEBHOOK_ID</Ic>. Missing headers, no webhook id, bad JSON or any other
              answer reject the event.
            </p>
            <Table
              head={["Event", "What the store does"]}
              rows={[
                [
                  <Ic key="1">CHECKOUT.ORDER.APPROVED</Ic>,
                  "Authorize the order, then capture or wait for the seller.",
                ],
                [
                  <Ic key="2">PAYMENT.CAPTURE.COMPLETED</Ic>,
                  "Confirm the capture. Counted once even if it arrives before the authorize step finishes.",
                ],
                [<Ic key="3">PAYMENT.AUTHORIZATION.VOIDED</Ic>, "Mark the order VOIDED."],
                [<Ic key="4">PAYMENT.CAPTURE.REFUNDED</Ic>, "Mark the order REFUNDED."],
              ]}
            />
            <p>
              Each event id is stored once. A redelivered id returns <Ic>DUPLICATE</Ic> and does
              nothing. If handling fails, the id is released and the server answers 500, so PayPal
              retries. The webhook log is on the Orders screen.
            </p>
          </Section>

          <Section id="api" title="REST API">
            <p>
              Admin routes need the <Ic>X-Admin-Token</Ic> header. Without <Ic>ADMIN_TOKEN</Ic> set
              on the backend they are switched off.
            </p>
            <Table
              head={["Method and path", "Access", "Purpose"]}
              rows={[
                [<Ic key="1">GET /health</Ic>, "public", "Status and whether PayPal is connected."],
                [<Ic key="2">POST /mcp</Ic>, "agent key", "MCP tools for agents."],
                [<Ic key="3">POST /api/keys</Ic>, "admin", "Create a key (raw key returned once)."],
                [<Ic key="4">GET /api/keys</Ic>, "admin", "List keys."],
                [<Ic key="5">POST /api/keys/{"{id}"}/revoke</Ic>, "admin", "Revoke a key."],
                [
                  <Ic key="6">GET /api/orders, GET /api/orders/{"{id}"}</Ic>,
                  "admin",
                  "Orders, with the event log for one order.",
                ],
                [
                  <Ic key="7">POST /api/orders/{"{id}"}/refund</Ic>,
                  "admin",
                  "Refund a captured order.",
                ],
                [
                  <Ic key="8">GET /api/approvals</Ic>,
                  "admin",
                  "Approval queue, optional ?status=PENDING.",
                ],
                [
                  <Ic key="9">POST /api/approvals/{"{id}"}/approve or /reject</Ic>,
                  "admin",
                  "Seller decision.",
                ],
                [
                  <Ic key="10">POST /api/approvals/expire</Ic>,
                  "admin",
                  "Void approvals past their 24 h deadline.",
                ],
                [
                  <Ic key="11">POST /api/webhooks/paypal</Ic>,
                  "PayPal signature",
                  "Webhook receiver.",
                ],
                [<Ic key="12">GET /api/webhooks/events</Ic>, "admin", "Webhook log."],
                [
                  <Ic key="13">POST /api/paypal/catalog/sync</Ic>,
                  "admin",
                  "Preview a read of the PayPal catalog.",
                ],
              ]}
            />
            <p>
              The full machine-readable description is at <Ic>/openapi.json</Ic> and <Ic>/docs</Ic>{" "}
              on the backend host (FastAPI).
            </p>
          </Section>

          <Section id="sandbox" title="Test on the PayPal sandbox">
            <ol className="list-decimal space-y-1 pl-5">
              <li>
                On developer.paypal.com choose <strong>Sandbox</strong>, then Apps and Credentials,
                create a Merchant app and copy the Client ID and Secret into <Ic>backend/.env</Ic>.
              </li>
              <li>
                Under Testing Tools, Sandbox Accounts, note the email and password of the Personal
                (buyer) account.
              </li>
              <li>
                Run a scenario. The script prints a PayPal link; open it and approve as the buyer.
              </li>
            </ol>
            <Code label="PowerShell">{`cd backend
python -m app.scripts.sandbox_e2e allow`}</Code>
            <Table
              head={["Scenario", "Expected", "Shows"]}
              rows={[
                [
                  <Ic key="1">allow</Ic>,
                  "CAPTURED",
                  "$36 inside the auto-approve limit: authorize, witness, capture.",
                ],
                [
                  <Ic key="2">approval</Ic>,
                  "CAPTURED",
                  "$72 waits as AUTHORIZED until the seller approves.",
                ],
                [<Ic key="3">reject</Ic>, "VOIDED", "Seller rejects, the authorization is voided."],
                [
                  <Ic key="4">deny</Ic>,
                  "DENIED",
                  "$216 is over the hard limit. PayPal is never called.",
                ],
              ]}
            />
            <p>
              Add <Ic>--refund</Ic> to the <Ic>allow</Ic> scenario to test refunds. Without a public
              webhook URL the script polls PayPal and runs the same handler a webhook would.
            </p>
          </Section>

          <Section id="deploy" title="Deploy">
            <ol className="list-decimal space-y-1 pl-5">
              <li>
                <strong>Database.</strong> Create a Postgres (Neon works) and copy its connection
                string into <Ic>DATABASE_URL</Ic>. Tables are created by{" "}
                <Ic>alembic upgrade head</Ic>, which the backend container runs on start.
              </li>
              <li>
                <strong>Backend on Render.</strong> New, Blueprint, pick the repository (
                <Ic>render.yaml</Ic>). Fill <Ic>DATABASE_URL</Ic>, <Ic>APP_URL</Ic> and the PayPal
                variables. <Ic>ADMIN_TOKEN</Ic> is generated for you.
              </li>
              <li>
                <strong>Webhook.</strong> In your PayPal sandbox app add a webhook for{" "}
                <Ic>https://BACKEND/api/webhooks/paypal</Ic> with the four events above, and put its
                id in <Ic>PAYPAL_WEBHOOK_ID</Ic>.
              </li>
              <li>
                <strong>Frontend on Vercel.</strong> Import the repository, set Root Directory to{" "}
                <Ic>frontend</Ic>, and set <Ic>NEXT_PUBLIC_API_BASE_URL</Ic> to the backend URL.
              </li>
            </ol>
          </Section>

          <Section id="security" title="Security">
            <ul className="list-disc space-y-1 pl-5">
              <li>Agent keys are stored as SHA-256 hashes and shown once.</li>
              <li>The price always comes from a server-side quote, never from the agent.</li>
              <li>The policy engine and every money step are code. The model never decides.</li>
              <li>PayPal webhooks are verified with PayPal and deduplicated by event id.</li>
              <li>
                Admin routes are off unless <Ic>ADMIN_TOKEN</Ic> is set. Rate limits apply.
              </li>
              <li>
                CORS allows only <Ic>APP_URL</Ic>. Secrets stay on the server.
              </li>
              <li>Sandbox only: the code points at the sandbox API by default.</li>
            </ul>
            <Note kind="warn">
              <Ic>NEXT_PUBLIC_*</Ic> variables are visible to everyone who opens the site. Never put
              a real secret in one.
            </Note>
          </Section>

          <Section id="limits" title="What is not built">
            <ul className="list-disc space-y-1 pl-5">
              <li>The audit grid screen and seller login (Auth.js).</li>
              <li>Audit runs and fix versions are not stored in the database yet.</li>
              <li>
                The PayPal money flow is tested against a mocked PayPal in the automated tests, and
                by hand on the sandbox with the script above. Run it yourself before trusting a
                result.
              </li>
              <li>
                Automatic expiry of stale approvals needs a scheduler to call the expire route.
              </li>
            </ul>
          </Section>

          <Section id="troubleshooting" title="Troubleshooting">
            <Table
              head={["Symptom", "Cause and fix"]}
              rows={[
                ["pip fails with a pydantic-core conflict", "Python 3.14. Use 3.12 or 3.13."],
                [
                  "PayPalConfigError: Set PAYPAL_CLIENT_ID...",
                  "The variables are not in backend/.env or the shell.",
                ],
                [
                  "401 invalid_client from PayPal",
                  "Wrong Client ID or Secret, or live keys used with the sandbox URL.",
                ],
                [
                  "Keys or Orders screen says the token was rejected",
                  "The token typed does not equal ADMIN_TOKEN on the backend.",
                ],
                [
                  "Order stays CREATED",
                  "The buyer has not approved, or the webhook does not reach the backend.",
                ],
                [
                  "WEBHOOK_REJECTED",
                  "PAYPAL_WEBHOOK_ID is not the id of the webhook that sent the event.",
                ],
                [
                  "WITNESS_MISMATCH",
                  "PayPal's copy differs from ours. The order log names the field, and the authorization is voided.",
                ],
                [
                  "verify_benchmark fails on Windows",
                  "Line endings changed. Pull the latest .gitattributes and re-checkout the files.",
                ],
              ]}
            />
          </Section>
        </main>
      </div>

      <SiteFooter />
    </div>
  );
}
