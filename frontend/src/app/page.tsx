import Link from "next/link";

/** Placeholder landing page (module M16, owner: P3). Replace with the real sections. */
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-4xl font-bold">ShelfReady</h1>
      <p className="mt-4 text-lg">
        Make a small store buyable by AI shopping agents, then prove it: the same buyer agent fails
        before and succeeds after. Runs on the PayPal sandbox only.
      </p>
      <p className="mt-6">
        <Link
          href="/app"
          className="inline-block rounded bg-[#0b6e4f] px-4 py-2 font-semibold text-white focus:outline-2 focus:outline-offset-2"
        >
          Try the demo
        </Link>
      </p>
    </main>
  );
}
