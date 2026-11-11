import { NextResponse } from "next/server";
import { STORE_TOOL_DEFS } from "@/lib/mcp";

export const dynamic = "force-dynamic";

/** Machine-readable store manifest for agents (owner: P2). Extend with policy and shipping data. */
export function GET() {
  const base = process.env.APP_URL ?? "http://localhost:3000";
  return NextResponse.json({
    name: "ShelfReady demo store",
    sandboxOnly: true,
    mcp: { url: `${base}/mcp`, tools: STORE_TOOL_DEFS.map((t) => t.name) },
  });
}
