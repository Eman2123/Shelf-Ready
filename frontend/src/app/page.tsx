import Link from "next/link";

/** Placeholder landing page (module M16, owner: P3). Replace with the real sections. */
export default function Home() {
  return (
    <main className="mx-auto max-w-5xl px-4 py-16">
      <p className="border-b-4 border-double border-ink pb-2 font-mono text-xs font-bold uppercase">
        Shelf Ready · PayPal sandbox only
      </p>
      <h1 className="mt-8 font-display text-6xl font-bold leading-[0.92] tracking-tight md:text-8xl">
        Same agent.
        <br />
        Same task.
        <br />
        <span className="text-signal">New store.</span>
      </h1>
      <p className="mt-8 max-w-xl text-lg">
        Make a small store buyable by AI shopping agents, then prove it: the same buyer agent fails
        before and succeeds after. Runs on the PayPal sandbox only.
      </p>
      <p className="mt-8">
        <Link
          href="/app"
          className="inline-flex min-h-11 items-center bg-signal px-6 text-sm font-extrabold uppercase tracking-wide text-white hover:bg-ink"
        >
          Try the demo
        </Link>
      </p>
    </main>
  );
}
