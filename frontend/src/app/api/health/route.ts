import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** Used by the keep-alive ping (GitHub Actions) and uptime checks. Never touches secrets. */
export function GET() {
  return NextResponse.json({
    status: "ok",
    service: "shelfready",
    demoMode: process.env.DEMO_MODE === "true",
    sandboxOnly: true,
  });
}
