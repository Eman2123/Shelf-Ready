/** Dashboard shell (route /app). Screens are added by their owners; see docs/TEAM.md. */
const screens = [
  { name: "Connect and import", owner: "P2", tier: 1 },
  { name: "Audit grid", owner: "P2", tier: 1 },
  { name: "Fix review", owner: "P3 (data from P2)", tier: 1 },
  { name: "Policy", owner: "P1", tier: 1 },
  { name: "Agent keys", owner: "P1", tier: 1 },
  { name: "Agent test", owner: "P3", tier: 1 },
  { name: "Orders and approvals", owner: "P1", tier: 1 },
  { name: "Report", owner: "P3", tier: 1 },
];

export default function DashboardHome() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl font-bold">Dashboard (foundation)</h1>
      <p className="mt-2">
        Demo mode. Nothing here is built yet; this list is the build checklist.
      </p>
      <ul className="mt-6 list-disc pl-6">
        {screens.map((s) => (
          <li key={s.name}>
            {s.name} - Tier {s.tier} - owner {s.owner}
          </li>
        ))}
      </ul>
    </main>
  );
}
