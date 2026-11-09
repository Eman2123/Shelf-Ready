/** Marks hand-written fixture data so it is never mistaken for a real run. */
export function SampleBadge() {
  return (
    <span className="border-2 border-dashed border-ink px-2 py-0.5 font-mono text-xs font-bold">
      SAMPLE
    </span>
  );
}
