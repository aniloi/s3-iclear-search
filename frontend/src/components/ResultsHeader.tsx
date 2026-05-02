/** Search metadata header above the results table. */

import type { SearchReportData } from "../types";

interface ResultsHeaderProps {
  report: SearchReportData;
}

export default function ResultsHeader({ report }: ResultsHeaderProps) {
  return (
    <div className="space-y-1 mb-4" data-testid="results-header">
      <h2 className="text-lg font-semibold text-slate-800">
        Search Results for {report.date}
      </h2>
      <div className="flex flex-wrap gap-4 text-sm text-slate-600">
        <span>
          Bucket: <span className="font-mono">{report.bucket}</span>
        </span>
        <span>Profile: {report.profile}</span>
        <span>Files searched: {report.filesSearched}</span>
        {report.filesFailed > 0 && (
          <span className="text-amber-600 font-medium">
            Files failed: {report.filesFailed}
          </span>
        )}
      </div>
      <div className="text-sm font-medium">
        <span className="text-green-600">{report.summary.found}</span>
        <span className="text-slate-500">/{report.summary.total} IDs found</span>
      </div>
    </div>
  );
}
