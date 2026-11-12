import { PageTitle } from "@/components/ui";
import { FixReviewView } from "@/components/fix-review/fix-review-view";

export const metadata = { title: "Fix review · ShelfReady" };

/** Fix review screen (owner: B), built over A's fix engine. Three lanes plus the proof counter. */
export default function FixReviewPage() {
  return (
    <div>
      <PageTitle icon="fix">Fix review</PageTitle>
      <p className="mt-3 mb-6 max-w-xl">
        Every proposed value must be found in the source or come from the seller. Anything else is
        blocked.
      </p>
      <FixReviewView />
    </div>
  );
}
