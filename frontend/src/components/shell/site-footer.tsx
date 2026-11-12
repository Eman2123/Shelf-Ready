import Link from "next/link";
import { Icon, type IconName } from "@/components/ui";
import { LogoMark } from "@/components/ui/logo";

const REPO = "https://github.com/Eman2123/Shelf-Ready";

const PRODUCT: { label: string; href: string; icon: IconName }[] = [
  { label: "Dashboard", href: "/app", icon: "report" },
  { label: "Agent test", href: "/app/agent-test", icon: "agent" },
  { label: "Orders", href: "/app/orders", icon: "orders" },
  { label: "Report", href: "/app/report", icon: "report" },
];

/** Shared by the landing page and the dashboard. */
export function SiteFooter() {
  return (
    <footer className="mt-auto border-t-4 border-double border-ink bg-paper">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <p className="flex items-center gap-2.5 font-display text-2xl font-bold">
            <LogoMark size={28} /> Shelf Ready
          </p>
          <p className="mt-3 max-w-sm text-sm">
            Make a small store buyable by AI shopping agents, with rule-guarded PayPal checkout and
            a before and after test that proves it.
          </p>
        </div>
        <nav aria-label="Product">
          <p className="font-mono text-xs font-bold uppercase text-mute">Product</p>
          <ul className="mt-3 space-y-2 text-sm font-semibold">
            {PRODUCT.map((p) => (
              <li key={p.href}>
                <Link href={p.href} className="inline-flex items-center gap-2 hover:underline">
                  <Icon name={p.icon} size={16} /> {p.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <nav aria-label="Project">
          <p className="font-mono text-xs font-bold uppercase text-mute">Project</p>
          <ul className="mt-3 space-y-2 text-sm font-semibold">
            <li>
              <a href={REPO} className="inline-flex items-center gap-2 hover:underline">
                <Icon name="code" size={16} /> Source on GitHub
              </a>
            </li>
            <li className="flex items-center gap-2">
              <Icon name="lock" size={16} /> MIT licence
            </li>
            <li className="flex items-center gap-2">
              <Icon name="flask" size={16} /> PayPal sandbox only
            </li>
          </ul>
        </nav>
      </div>
      <div className="border-t border-ink">
        <p className="mx-auto max-w-6xl px-4 py-3 font-mono text-xs uppercase text-mute">
          Fictional store: Tidewell Goods · Scripted agents are not language models · No real money
          moves
        </p>
      </div>
    </footer>
  );
}
