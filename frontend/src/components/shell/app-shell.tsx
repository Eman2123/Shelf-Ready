"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Icon, type IconName } from "@/components/ui";
import { Logo } from "@/components/ui/logo";
import { SiteFooter } from "./site-footer";

/** Dashboard steps in seller order. Screens without an href are not built yet. */
const NAV = [
  { n: "01", label: "Connect", icon: "connect" as IconName, href: "/app/connect" },
  { n: "02", label: "Audit", icon: "audit" as IconName, href: null },
  { n: "03", label: "Fix review", icon: "fix" as IconName, href: "/app/fix-review" },
  { n: "04", label: "Agent test", icon: "agent" as IconName, href: "/app/agent-test" },
  { n: "05", label: "Keys", icon: "key" as IconName, href: "/app/keys" },
  { n: "06", label: "Orders", icon: "orders" as IconName, href: "/app/orders" },
  { n: "07", label: "Report", icon: "report" as IconName, href: "/app/report" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-ink focus:p-3 focus:text-paper"
      >
        Skip to content
      </a>
      <header className="border-b-4 border-double border-ink">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-8 gap-y-3 px-4 py-4">
          <Logo href="/" />
          <nav aria-label="Main">
            <ol className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
              {NAV.map((item) => {
                const label = (
                  <>
                    <span className="inline-flex items-center gap-1.5">
                      <Icon name={item.icon} size={16} />
                      <span className="font-mono text-xs">{item.n}</span> {item.label}
                    </span>
                  </>
                );
                if (!item.href) {
                  return (
                    <li key={item.n} className="text-mute" title="Not built yet">
                      {label}
                    </li>
                  );
                }
                const active = pathname === item.href;
                return (
                  <li key={item.n}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={
                        active
                          ? "border-b-4 border-signal pb-0.5 font-extrabold"
                          : "pb-0.5 font-semibold hover:border-b-4 hover:border-ink"
                      }
                    >
                      {label}
                    </Link>
                  </li>
                );
              })}
            </ol>
          </nav>
          <p className="font-mono text-xs font-bold uppercase">PayPal sandbox only</p>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}
