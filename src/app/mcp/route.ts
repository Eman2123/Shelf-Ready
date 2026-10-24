import { NextResponse } from "next/server";
import { STORE_TOOL_DEFS } from "@/lib/mcp";

export const dynamic = "force-dynamic";

/**
 * Store MCP endpoint (owner: P2; P1 adds the agent-key check on every call).
 * TODO: replace with @modelcontextprotocol/sdk streamable HTTP transport.
 * For now GET lists the tool contract and POST is not implemented.
 */
export function GET() {
  return NextResponse.json({
    name: "shelfready-store",
    transport: "streamable-http (not implemented yet)",
    tools: STORE_TOOL_DEFS.map((t) => ({ name: t.name, description: t.description })),
  });
}

export function POST() {
  return NextResponse.json({ error: "not_implemented" }, { status: 501 });
}
