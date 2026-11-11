import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-xl px-4 py-16">
      <h1 className="font-display text-3xl font-bold">Page not found</h1>
      <p className="mt-2 text-sm">Nothing lives at this address.</p>
      <Link href="/app" className="mt-4 inline-block underline">
        Back to the dashboard
      </Link>
    </main>
  );
}
