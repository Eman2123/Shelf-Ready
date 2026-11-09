"use client";

import type { FixProposal } from "@/lib/contracts";
import { SAMPLE_PRODUCT, SOURCE_FIELD, SOURCE_TEXT, sampleFixes } from "@/lib/fixtures/fix-records";
import { laneOf, splitAtSnippet, unsupportedCounter, type Lane } from "@/lib/fix-review";
import { SampleBadge, StatusTag, type StatusKind } from "@/components/ui";

const LANES: { id: Lane; title: string; note: string; rule: string; kind: StatusKind }[] = [
  {
    id: "green",
    title: "Applied",
    note: "Value is quoted from the source.",
    rule: "border-ok",
    kind: "ok",
  },
  {
    id: "red",
    title: "Blocked",
    note: "The AI proposed a value the source never states.",
    rule: "border-signal",
    kind: "blocked",
  },
  {
    id: "yellow",
    title: "Needs seller",
    note: "The data is not in the source. Nothing is guessed.",
    rule: "border-wait",
    kind: "wait",
  },
];

const show = (v: unknown) =>
  v === null || v === undefined ? "(empty)" : typeof v === "string" ? v : JSON.stringify(v);

function SourceText({ snippet }: { snippet: string }) {
  const parts = splitAtSnippet(SOURCE_TEXT, snippet);
  if (!parts) return <p className="text-sm">{SOURCE_TEXT}</p>;
  return (
    <p className="text-sm">
      {parts.before}
      <mark className="bg-hilite px-0.5 font-bold text-ink">{parts.match}</mark>
      {parts.after}
    </p>
  );
}

function FixCard({ fix, lane, kind }: { fix: FixProposal; lane: Lane; kind: StatusKind }) {
  const ev = fix.evidence;
  return (
    <li className="border border-ink p-4 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono font-bold">{fix.field}</span>
        <StatusTag kind={kind} />
      </div>
      <dl className="mt-3 space-y-1">
        <div className="flex gap-2">
          <dt className="w-24 shrink-0 text-mute">Was</dt>
          <dd>{show(fix.oldValue)}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-24 shrink-0 text-mute">{lane === "red" ? "AI proposed" : "Now"}</dt>
          <dd className={lane === "red" ? "font-bold line-through decoration-2" : "font-bold"}>
            {show(fix.newValue)}
          </dd>
        </div>
      </dl>
      {lane === "yellow" && (
        <p className="mt-3">The seller must enter this value before it can be published.</p>
      )}
      {lane === "red" && fix.rejectionReason && (
        <p className="mt-3 bg-ink p-3 font-semibold text-white">No match. {fix.rejectionReason}</p>
      )}
      {ev && lane !== "yellow" && (
        <div className="mt-3 border-t border-ink pt-3">
          <p className="font-mono text-xs text-mute">
            {ev.sourceField} · {ev.method} · confidence {ev.confidence.toFixed(2)}
          </p>
          <div className="mt-1">
            <SourceText snippet={ev.sourceSnippet} />
          </div>
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
        className="grid items-end gap-x-8 gap-y-2 border-b-4 border-ink pb-6 md:grid-cols-[auto_1fr]"
      >
        <span
          className={`text-[9rem] font-extrabold leading-[0.8] tracking-[-0.06em] md:text-[13rem] ${
            c.unsupported === 0 ? "text-ink" : "text-signal"
          }`}
        >
          {c.unsupported}
        </span>
        <div className="pb-2">
          <p className="text-3xl font-extrabold leading-tight">
            Unsupported facts
            <br />
            in catalog.
          </p>
          <p className="mt-2 font-mono text-sm">
            {c.verified} of {c.total} fields verified
          </p>
        </div>
      </div>

      <p className="mt-4 flex flex-wrap items-center gap-3 text-sm">
        <SampleBadge />
        <span>
          Hand-written fixtures for {SAMPLE_PRODUCT.name}. Real fixes from the fix engine replace
          them when it is connected.
        </span>
      </p>

      <section aria-label="Source text" className="mt-6 border-b border-ink pb-4">
        <h2 className="font-mono text-xs font-bold uppercase">Source · {SOURCE_FIELD}</h2>
        <p className="mt-2 max-w-3xl text-lg">{SOURCE_TEXT}</p>
      </section>

      <div className="mt-8 grid gap-8 md:grid-cols-3">
        {LANES.map((lane) => {
          const items = fixes.filter((f) => laneOf(f) === lane.id);
          return (
            <section
              key={lane.id}
              aria-label={lane.title}
              className={`border-t-8 pt-3 ${lane.rule}`}
            >
              <header className="flex items-baseline justify-between gap-2">
                <h2 className="text-2xl font-extrabold uppercase tracking-tight">{lane.title}</h2>
                <span className="font-mono text-xl font-bold">{items.length}</span>
              </header>
              <p className="mt-1 text-sm text-mute">{lane.note}</p>
              <ul className="mt-4 space-y-3">
                {items.map((f) => (
                  <FixCard key={f.id} fix={f} lane={lane.id} kind={lane.kind} />
                ))}
                {items.length === 0 && <li className="text-sm text-mute">Nothing here.</li>}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
