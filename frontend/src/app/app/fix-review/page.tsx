import { FixReviewView } from "@/components/fix-review/fix-review-view";

export const metadata = { title: "Fix review · ShelfReady" };

/** Fix review screen (owner: B), built over A's fix engine. Three lanes plus the proof counter. */
export default function FixReviewPage() {
  return (
    <div>
      <h1 className="font-display text-6xl font-bold leading-none tracking-tight">Fix review</h1>
      <p className="mt-3 mb-6 max-w-xl">
        Every proposed value must be found in the source or come from the seller. Anything else is
        blocked.
      </p>
      <FixReviewView />
    </div>
  );
}
