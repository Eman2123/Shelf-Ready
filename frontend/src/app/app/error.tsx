"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <div role="alert" className="border-2 border-signal p-6">
      <h1 className="font-display text-2xl font-bold">Something went wrong</h1>
      <p className="mt-2 text-sm">This screen could not load. Your data was not changed.</p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 min-h-11 bg-ink px-6 text-sm font-extrabold uppercase text-paper"
      >
        Try again
      </button>
    </div>
  );
}
