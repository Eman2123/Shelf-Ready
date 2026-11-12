import { PageTitle } from "@/components/ui";
import { ReportView } from "@/components/report/report-view";

export const metadata = { title: "Report · ShelfReady" };

/** Report screen: the Readiness Receipt (PRD 4.8). Owner: B. */
export default function ReportPage() {
  return (
    <div>
      <PageTitle icon="report">Report</PageTitle>
      <div className="mt-6">
        <ReportView />
      </div>
    </div>
  );
}
