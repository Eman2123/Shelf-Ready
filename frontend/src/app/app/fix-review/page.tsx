import { FixReviewView } from "@/components/fix-review/fix-review-view";

export const metadata = { title: "Fix review · ShelfReady" };

/** Fix review screen (owner: B), built over A's fix engine. Three lanes plus the proof counter. */
export default function FixReviewPage() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-bold">Fix review</h1>
      <p className="mt-1 mb-4 text-gray-700">
        Every proposed value must be found in the source or come from the seller. Anything else is
        blocked.
      </p>
      <FixReviewView />
    </main>
  );
}
