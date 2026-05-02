/** Complete results view: header + warnings + toolbar + table. */

import type { SearchTab } from "../types";
import { getExportUrl } from "../api";
import ResultsHeader from "./ResultsHeader";
import ResultsTable from "./ResultsTable";
import WarningsBanner from "./WarningsBanner";

interface ResultsViewProps {
  tab: SearchTab;
}

export default function ResultsView({ tab }: ResultsViewProps) {
  const report = tab.report;
  const isSearching = tab.status === "searching";

  return (
    <div data-testid="results-view">
      {report && <ResultsHeader report={report} />}

      <WarningsBanner warnings={tab.warnings} />

      {/* Export buttons */}
      {tab.status === "complete" && (
        <div className="flex gap-2 mb-4" data-testid="export-buttons">
          <a
            href={getExportUrl(tab.id, "json")}
            download
            className="px-3 py-1.5 text-xs border border-slate-300 rounded hover:bg-slate-50 transition-colors"
            data-testid="export-json-button"
          >
            📥 Export JSON
          </a>
          <a
            href={getExportUrl(tab.id, "csv")}
            download
            className="px-3 py-1.5 text-xs border border-slate-300 rounded hover:bg-slate-50 transition-colors"
            data-testid="export-csv-button"
          >
            📥 Export CSV
          </a>
        </div>
      )}

      <ResultsTable
        results={report?.results ?? tab.results}
        isSearching={isSearching}
      />
    </div>
  );
}
