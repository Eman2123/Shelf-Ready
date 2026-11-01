"use client";

import type { FixProposal } from "@/lib/contracts";
import { SAMPLE_PRODUCT, SOURCE_FIELD, SOURCE_TEXT, sampleFixes } from "@/lib/fixtures/fix-records";
import { laneOf, splitAtSnippet, unsupportedCounter, type Lane } from "@/lib/fix-review";

const LANES: { id: Lane; title: string; note: string; box: string; badge: string }[] = [
  {
    id: "green",
    title: "Applied",
    note: "Value is quoted from the source.",
    box: "border-green-500 bg-green-50",
    badge: "bg-green-100 text-green-900",
  },
  {
    id: "red",
    title: "Blocked by validator",
    note: "The AI proposed a value the source never states.",
    box: "border-red-500 bg-red-50",
    badge: "bg-red-100 text-red-900",
  },
  {
    id: "yellow",
    title: "Needs seller input",
    note: "The data is not in the source. Nothing is guessed.",
    box: "border-yellow-500 bg-yellow-50",
    badge: "bg-yellow-100 text-yellow-900",
  },
];

const show = (v: unknown) =>
  v === null || v === undefined ? "(empty)" : typeof v === "string" ? v : JSON.stringify(v);

function SourceText({ snippet }: { snippet: string }) {
  const parts = splitAtSnippet(SOURCE_TEXT, snippet);
  if (!parts) return <p className="text-sm text-gray-800">{SOURCE_TEXT}</p>;
  return (
    <p className="text-sm text-gray-800">
      {parts.before}
      <mark className="rounded bg-yellow-200 px-0.5 font-semibold text-black">{parts.match}</mark>
      {parts.after}
    </p>
  );
}

function FixCard({ fix, lane }: { fix: FixProposal; lane: Lane }) {
  const ev = fix.evidence;
  return (
    <li className="rounded border bg-white p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono font-semibold">{fix.field}</span>
        <span className="text-xs text-gray-600">{fix.status}</span>
      </div>
      <p className="mt-2">
        <span className="text-gray-600">Was:</span> {show(fix.oldValue)}
      </p>
      <p>
        <span className="text-gray-600">{lane === "red" ? "AI proposed:" : "Now:"}</span>{" "}
        <span className={lane === "red" ? "line-through" : "font-medium"}>
          {show(fix.newValue)}
        </span>
      </p>
      {lane === "yellow" && (
        <p className="mt-2 text-gray-700">
          The seller must enter this value before it can be published.
        </p>
      )}
      {lane === "red" && fix.rejectionReason && (
        <p className="mt-2 rounded bg-red-100 p-2 text-red-900">{fix.rejectionReason}</p>
      )}
      {ev && lane !== "yellow" && (
        <div className="mt-2 rounded border bg-gray-50 p-2">
          <p className="text-xs text-gray-600">
            Source: <span className="font-mono">{ev.sourceField}</span> · {ev.method} · confidence{" "}
            {ev.confidence.toFixed(2)}
          </p>
          <div className="mt-1">
            <SourceText snippet={ev.sourceSnippet} />
          </div>
          {lane === "red" && (
            <p className="mt-1 text-xs text-red-800">No match in the source text.</p>
          )}
        </div>
      )}
    </li>
  );
}

export function FixReviewView({ fixes = sampleFixes }: { fixes?: FixProposal[] }) {
  const c = unsupportedCounter(fixes, SOURCE_TEXT);
  return (
    <div>
      <div
        role="status"
        className={`sticky top-0 z-10 rounded border-2 p-3 ${c.unsupported === 0 ? "border-green-600 bg-green-50" : "border-red-600 bg-red-50"}`}
      >
        <p className="font-semibold">
          Unsupported facts in catalog: {c.unsupported}{" "}
          <span className="font-normal">
            ({c.verified} of {c.total} fields verified)
          </span>
        </p>
      </div>

      <p className="mt-3 rounded border border-yellow-400 bg-yellow-50 p-3 text-sm">
        <span className="mr-2 rounded bg-yellow-300 px-1.5 py-0.5 text-xs font-bold">SAMPLE</span>
        Hand-written fixtures for {SAMPLE_PRODUCT.name}. Real fixes from the fix engine (no run_id
        yet) replace them when it is connected.
      </p>

      <section className="mt-4 rounded border p-3">
        <h2 className="text-sm font-semibold">
          Source text ({SOURCE_FIELD}) · {SAMPLE_PRODUCT.name}
        </h2>
        <p className="mt-1 text-sm text-gray-800">{SOURCE_TEXT}</p>
      </section>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {LANES.map((lane) => {
          const items = fixes.filter((f) => laneOf(f) === lane.id);
          return (
            <section
              key={lane.id}
              aria-label={lane.title}
              className={`rounded border-2 p-3 ${lane.box}`}
            >
              <header className="flex items-center justify-between gap-2">
                <h2 className="font-semibold">{lane.title}</h2>
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${lane.badge}`}>
                  {items.length}
                </span>
              </header>
              <p className="mt-1 text-xs text-gray-700">{lane.note}</p>
              <ul className="mt-3 space-y-2">
                {items.map((f) => (
                  <FixCard key={f.id} fix={f} lane={lane.id} />
                ))}
                {items.length === 0 && <li className="text-sm text-gray-600">Nothing here.</li>}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
