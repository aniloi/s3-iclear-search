/** Interactive sortable/filterable results table with expandable rows. */

import { useMemo, useState } from "react";
import type { SearchResultData } from "../types";

interface ResultsTableProps {
  results: SearchResultData[];
  isSearching?: boolean;
}

type SortColumn = "id" | "status" | "files" | "matchCount";
type SortDir = "asc" | "desc";
type StatusFilter = "all" | "found" | "not_found";

export default function ResultsTable({ results, isSearching }: ResultsTableProps) {
  const [sortCol, setSortCol] = useState<SortColumn>("id");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const toggleSort = (col: SortColumn) => {
    if (sortCol === col) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const filtered = useMemo(() => {
    let items = [...results];

    // Status filter
    if (statusFilter === "found") items = items.filter((r) => r.found);
    else if (statusFilter === "not_found") items = items.filter((r) => !r.found);

    // Text search
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      items = items.filter((r) => r.id.toLowerCase().includes(q));
    }

    // Sort
    items.sort((a, b) => {
      let cmp = 0;
      switch (sortCol) {
        case "id":
          cmp = a.id.localeCompare(b.id);
          break;
        case "status":
          cmp = Number(a.found) - Number(b.found);
          break;
        case "files":
          cmp = a.files.length - b.files.length;
          break;
        case "matchCount":
          cmp = a.totalMatchCount - b.totalMatchCount;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });

    return items;
  }, [results, statusFilter, searchQuery, sortCol, sortDir]);

  const sortIndicator = (col: SortColumn) =>
    sortCol === col ? (sortDir === "asc" ? " ↑" : " ↓") : "";

  return (
    <div data-testid="results-table-container">
      {/* Toolbar */}
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <div className="flex gap-1" data-testid="status-filter">
          {(["all", "found", "not_found"] as StatusFilter[]).map((f) => (
            <button
              key={f}
              className={`px-2 py-1 text-xs rounded ${
                statusFilter === f
                  ? "bg-blue-100 text-blue-700 font-medium"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
              onClick={() => setStatusFilter(f)}
              data-testid={`filter-${f}`}
            >
              {f === "all" ? "All" : f === "found" ? "Found" : "Not Found"}
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search IDs..."
          className="px-2 py-1 text-sm border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          data-testid="results-search-input"
          aria-label="Filter results by ID"
        />
        <span className="text-xs text-slate-500 ml-auto">
          {filtered.length} of {results.length} results
        </span>
      </div>

      {/* Table */}
      <table className="w-full text-sm border-collapse" data-testid="results-table">
        <thead>
          <tr className="border-b border-slate-200 text-left">
            <th
              className="py-2 px-3 cursor-pointer hover:text-blue-600 select-none"
              onClick={() => toggleSort("id")}
            >
              ID{sortIndicator("id")}
            </th>
            <th
              className="py-2 px-3 cursor-pointer hover:text-blue-600 select-none w-24"
              onClick={() => toggleSort("status")}
            >
              Status{sortIndicator("status")}
            </th>
            <th
              className="py-2 px-3 cursor-pointer hover:text-blue-600 select-none"
              onClick={() => toggleSort("files")}
            >
              File(s){sortIndicator("files")}
            </th>
            <th
              className="py-2 px-3 cursor-pointer hover:text-blue-600 select-none w-28"
              onClick={() => toggleSort("matchCount")}
            >
              Matches{sortIndicator("matchCount")}
            </th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <ResultRow
              key={r.id}
              result={r}
              isSearching={isSearching}
              expanded={expandedIds.has(r.id)}
              onToggle={() => toggleExpand(r.id)}
            />
          ))}
          {filtered.length === 0 && (
            <tr>
              <td colSpan={4} className="py-8 text-center text-slate-400">
                No results to display
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ResultRow({
  result,
  isSearching,
  expanded,
  onToggle,
}: {
  result: SearchResultData;
  isSearching?: boolean;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasContext = result.files.some((f) => f.context.length > 0);

  return (
    <>
      <tr
        className={`border-b border-slate-100 hover:bg-slate-50 ${
          hasContext ? "cursor-pointer" : ""
        }`}
        onClick={hasContext ? onToggle : undefined}
        data-testid={`result-row-${result.id}`}
        tabIndex={hasContext ? 0 : undefined}
        onKeyDown={
          hasContext
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onToggle();
                }
              }
            : undefined
        }
        role={hasContext ? "button" : undefined}
        aria-expanded={hasContext ? expanded : undefined}
      >
        <td className="py-2 px-3 font-mono text-xs">{result.id}</td>
        <td className="py-2 px-3">
          {result.found ? (
            <span className="text-green-600">✅ Found</span>
          ) : isSearching ? (
            <span className="text-slate-400">⏳ Pending</span>
          ) : (
            <span className="text-red-500">❌ Not Found</span>
          )}
        </td>
        <td className="py-2 px-3 text-xs text-slate-600">
          {result.files.map((f) => f.filename).join(", ") || "—"}
        </td>
        <td className="py-2 px-3 text-xs">{result.totalMatchCount}</td>
      </tr>
      {expanded && hasContext && (
        <tr>
          <td colSpan={4} className="bg-slate-50 px-6 py-3">
            {result.files.map((fm) => (
              <div key={fm.filename} className="mb-3 last:mb-0">
                <p className="text-xs font-medium text-slate-700 mb-1">
                  {fm.filename} ({fm.matchCount} match{fm.matchCount !== 1 ? "es" : ""})
                </p>
                <div className="space-y-0.5">
                  {fm.context.map((line, i) => (
                    <pre
                      key={i}
                      className="text-xs font-mono text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200 overflow-x-auto"
                    >
                      {line}
                    </pre>
                  ))}
                </div>
              </div>
            ))}
          </td>
        </tr>
      )}
    </>
  );
}
