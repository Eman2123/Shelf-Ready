# Shelf Ready

Make small online stores buyable by AI shopping agents: audit product data, fix it with evidence, and open a rule-guarded PayPal checkout. Built for the PayPal AI Hackathon 2026.

> **Sandbox only.** This project uses the PayPal sandbox. No real money moves anywhere in this repository.

## What it does

AI shopping agents skip stores whose product data is vague and whose checkout needs a human. Shelf Ready:

1. **Audits** a store (demo store, CSV, or product feed URL) and scores how ready it is for agents.
2. **Fixes** product data with AI. Every proposed value carries its source; anything the source does not state becomes a question to the seller, never an invention.
3. **Opens a guarded purchase path**: a store MCP server, scoped agent keys, and a deterministic policy engine. Only code, never the model, decides whether an order may be created or captured.
4. **Proves it**: the same buyer agent runs a fixed 10-task benchmark before and after the fixes.

How it relates to PayPal's own Agent Ready and Store Sync: those get a catalog in front of agents and accept agent payments. Shelf Ready checks that the data is good enough for an agent to buy correctly and that the purchase is safe for the seller.

## Status

Foundation commit. The folder structure, shared contracts (Zod), database schema, stubs for every module, CI and safety-test placeholders are in place. Feature modules are being built in tiers; see `docs/` for the plan.

## Stack

Next.js (App Router) and TypeScript, Tailwind, AG Grid, Postgres with Drizzle, Vercel AI SDK with an OpenAI-compatible provider switch (AIML API or Gemini), Model Context Protocol SDK, PayPal sandbox REST API, Vitest, GitHub Actions with CodeQL.

## Getting started

Requires Node 20 or newer.

```bash
npm install
cp .env.example .env.local   # DEMO_MODE=true needs no other secrets
npm run dev                  # http://localhost:3000
```

Scripts: `dev`, `build`, `lint`, `typecheck`, `test`, `format`, `db:generate`, `db:migrate`, `seed:demo`, `bench:run`, `bench:record`.

Keep API keys server-side only. Never prefix a secret with `NEXT_PUBLIC_`.

## Repository layout

```
src/app              dashboard, demo store, API routes, /mcp, /.well-known/agent-store.json
src/lib/contracts    shared Zod schemas: the contracts between modules
src/lib/paypal       PayPal sandbox client (Orders, Catalog, Webhooks)
src/lib/import       CSV and feed importers
src/lib/connector    store scan and normalisation
src/lib/audit        scoring rules and AI rubric
src/lib/fixes        fix proposals, provenance, rollback
src/lib/agent-ready  Catalog patch, JSON-LD, agent manifest
src/lib/mcp          store MCP server tools
src/lib/policy       deterministic policy engine
src/lib/keys         agent keys, scopes, budgets, kill switch
src/lib/orders       guarded order creation
src/lib/approvals    signed single-use approval links
src/lib/webhooks     verified, idempotent webhook handling
src/lib/agent        buyer agent (before and after modes)
src/lib/benchmark    the 10 fixed benchmark tasks
src/lib/ai           provider switch
src/db               Drizzle schema
src/components/ui    shared UI kit
scripts              seed-demo, run-benchmark, record-run
tests                contract and safety tests
```

## Safety principles

- AI helps, rules decide. Only deterministic code can create or capture an order.
- AI never invents product facts; missing data becomes a question to the seller.
- Product text is untrusted input and is never executed as instructions.
- Every agent action and policy decision is logged.

## Tools used

AI model access goes through the Vercel AI SDK with an OpenAI-compatible provider (AIML API, or Gemini as an alternative). The model is used for the audit rubric, fix extraction (structured output validated by Zod), and the buyer agent. PayPal Agent Toolkit and MCP are used by the buyer agent and as a read-only verifier. This section is finalised before submission.

## Licence

MIT. See `LICENSE`.
