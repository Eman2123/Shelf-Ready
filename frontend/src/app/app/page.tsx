import Link from "next/link";
import { Icon, PageTitle, type IconName } from "@/components/ui";

export const metadata = { title: "Dashboard · ShelfReady" };

type Screen = {
  name: string;
  blurb: string;
  icon: IconName;
  href: string | null;
  live: boolean;
};

/** Seller order. `live` = reads the running backend; otherwise it shows recorded runs. */
const screens: Screen[] = [
  {
    name: "Connect",
    blurb: "Backend and PayPal sandbox status, catalog preview.",
    icon: "connect",
    href: "/app/connect",
    live: true,
  },
  {
    name: "Audit grid",
    blurb: "Per-product readiness score. Not built yet.",
    icon: "audit",
    href: null,
    live: false,
  },
  {
    name: "Fix review",
    blurb: "Evidence-backed fixes in three lanes.",
    icon: "fix",
    href: "/app/fix-review",
    live: false,
  },
  {
    name: "Agent test",
    blurb: "Same agent, same task, before and after.",
    icon: "agent",
    href: "/app/agent-test",
    live: false,
  },
  {
    name: "Agent keys",
    blurb: "Create keys with limits. Revoke any time.",
    icon: "key",
    href: "/app/keys",
    live: true,
  },
  {
    name: "Orders & approvals",
    blurb: "Pipeline per order, approve, reject, refund.",
    icon: "orders",
    href: "/app/orders",
    live: true,
  },
  {
    name: "Report",
    blurb: "Recorded benchmark with a verifiable fingerprint.",
    icon: "report",
    href: "/app/report",
    live: false,
  },
];

export default function DashboardHome() {
  return (
    <div>
      <PageTitle icon="report">Dashboard</PageTitle>
      <p className="mt-3 max-w-xl">
        Seven screens, in seller order. <strong>Live</strong> screens talk to the running backend
        and the PayPal sandbox. <strong>Recorded</strong> screens show saved benchmark runs.
      </p>
      <ul className="mt-8 grid border-b-2 border-r-2 border-ink sm:grid-cols-2 lg:grid-cols-3">
        {screens.map((s) => {
          const body = (
            <>
              <span className="flex items-center justify-between">
                <Icon name={s.icon} size={28} />
                <span
                  className={`font-mono text-xs font-bold uppercase ${s.live ? "text-ok" : "text-mute"}`}
                >
                  {s.href ? (s.live ? "Live" : "Recorded") : "Not built"}
                </span>
              </span>
              <span className="mt-4 block font-display text-2xl font-bold">{s.name}</span>
              <span className="mt-1 block text-sm">{s.blurb}</span>
            </>
          );
          return (
            <li key={s.name} className="border-l-2 border-t-2 border-ink bg-paper">
              {s.href ? (
                <Link href={s.href} className="block h-full p-5 hover:bg-hilite">
                  {body}
                </Link>
              ) : (
                <div className="h-full p-5 text-mute">{body}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
