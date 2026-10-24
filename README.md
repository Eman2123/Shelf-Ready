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

Day 1 of the build (PRD v3.2 in `docs/`). The FastAPI backend skeleton and the Next.js UI shell are in place; feature modules are built by priority (P0, P1, P2). `legacy-ts/` holds the earlier TypeScript foundation as a porting reference only.

## Stack

Backend: FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy 2 + Alembic on Postgres, httpx, OpenAI-compatible SDK for AI (AIML API, Gemini backup), official `mcp` Python SDK for the store MCP, PayPal sandbox REST API, pytest, ruff, GitHub Actions with CodeQL.
Frontend: Next.js 15 (App Router), TypeScript, Tailwind, AG Grid. UI only, no business logic.

## Getting started

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload                        # http://127.0.0.1:8000/health
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev                                          # http://localhost:3000
```

Copy `.env.example` to `.env` and fill the PayPal sandbox values. Keep API keys server-side only.

## Repository layout

```
backend/app/main.py        FastAPI app (routers, /mcp mount, /.well-known)
backend/app/contracts/     Pydantic contracts between modules
backend/app/services/      paypal, policy, keys, orders, approvals, webhooks (P1)
                           importer, connector, audit, fixes, agent_ready, mcp_store (P2)
                           agent, benchmark, fixtures (P3); receipt, ai (shared)
backend/app/scripts/       seed_demo, run_benchmark, record_run, verify_receipt
backend/tests/             pytest
frontend/src/app/          landing, dashboard screens, demo-store
frontend/src/components/   shared UI kit
frontend/src/lib/api/      generated API types
docs/                      PRD v3.2, ADRs, archive of older versions
legacy-ts/                 old TS foundation, reference only
```

## License

MIT. See `LICENSE`.
