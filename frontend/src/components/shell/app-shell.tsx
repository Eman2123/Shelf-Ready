"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

/** Dashboard steps in seller order. Screens without an href are not built yet. */
const NAV = [
  { n: "01", label: "Connect", href: null },
  { n: "02", label: "Audit", href: null },
  { n: "03", label: "Fix review", href: "/app/fix-review" },
  { n: "04", label: "Agent test", href: "/app/agent-test" },
  { n: "05", label: "Orders", href: null },
  { n: "06", label: "Report", href: "/app/report" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-ink focus:p-3 focus:text-paper"
      >
        Skip to content
      </a>
      <header className="border-b-4 border-double border-ink">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-8 gap-y-3 px-4 py-4">
          <Link href="/app" className="font-display text-2xl font-bold tracking-tight">
            Shelf Ready
          </Link>
          <nav aria-label="Main">
            <ol className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
              {NAV.map((item) => {
                const label = (
                  <>
                    <span className="font-mono text-xs">{item.n}</span> {item.label}
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
      <main id="main" tabIndex={-1} className="mx-auto max-w-6xl px-4 py-8">
        {children}
      </main>
    </div>
  );
}
