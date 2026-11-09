import Link from "next/link";

/** Dashboard home (route /app). Screens are added by their owners; see docs/TEAM.md. */
const screens = [
  { name: "Connect and import", owner: "P2", tier: 1, href: null },
  { name: "Audit grid", owner: "P2", tier: 1, href: null },
  { name: "Fix review", owner: "P3 (data from P2)", tier: 1, href: "/app/fix-review" },
  { name: "Policy", owner: "P1", tier: 1, href: null },
  { name: "Agent keys", owner: "P1", tier: 1, href: null },
  { name: "Agent test", owner: "P3", tier: 1, href: "/app/agent-test" },
  { name: "Orders and approvals", owner: "P1", tier: 1, href: null },
  { name: "Report", owner: "P3", tier: 1, href: null },
] as const;

export default function DashboardHome() {
  return (
    <div>
      <h1 className="text-5xl font-extrabold uppercase leading-none tracking-tight">Dashboard</h1>
      <p className="mt-3 max-w-xl">
        Demo mode. Built screens are linked; the rest is the build checklist.
      </p>
      <ul className="mt-8 border-t-4 border-ink">
        {screens.map((s) => (
          <li
            key={s.name}
            className="grid grid-cols-[1fr_auto] gap-4 border-b border-ink py-3 sm:grid-cols-[2fr_1fr_auto]"
          >
            {s.href ? (
              <Link
                href={s.href}
                className="font-extrabold underline decoration-2 underline-offset-4"
              >
                {s.name}
              </Link>
            ) : (
              <span className="text-mute">{s.name}</span>
            )}
            <span className="hidden font-mono text-sm sm:block">owner {s.owner}</span>
            <span className="font-mono text-sm">Tier {s.tier}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
