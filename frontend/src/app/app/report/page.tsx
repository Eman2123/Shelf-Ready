import { ReportView } from "@/components/report/report-view";

export const metadata = { title: "Report · ShelfReady" };

/** Report screen: the Readiness Receipt (PRD 4.8). Owner: B. */
export default function ReportPage() {
  return (
    <div>
      <h1 className="font-display text-6xl font-bold leading-none tracking-tight">Report</h1>
      <div className="mt-6">
        <ReportView />
      </div>
    </div>
  );
}
