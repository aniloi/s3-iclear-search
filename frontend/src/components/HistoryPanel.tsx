/** Search history list in the sidebar. */

import type { SearchHistoryEntry } from "../types";

interface HistoryPanelProps {
  history: SearchHistoryEntry[];
  onReopen: (searchId: string) => void;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function statusBadge(status: string): string {
  switch (status) {
    case "completed":
      return "✅";
    case "cancelled":
      return "⏹";
    case "failed":
      return "❌";
    default:
      return "⏳";
  }
}

export default function HistoryPanel({ history, onReopen }: HistoryPanelProps) {
  return (
    <div className="p-4 border-t border-slate-200" data-testid="history-panel">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
        History
      </h3>
      {history.length === 0 ? (
        <p className="text-xs text-slate-400">No searches yet</p>
      ) : (
        <ul className="space-y-1.5">
          {history.map((entry) => (
            <li key={entry.search_id}>
              <button
                className="w-full text-left px-2 py-1.5 rounded hover:bg-slate-100 transition-colors"
                onClick={() => onReopen(entry.search_id)}
                data-testid={`history-entry-${entry.search_id}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-700">
                    {entry.date} / {entry.profile}
                  </span>
                  <span className="text-xs">{statusBadge(entry.status)}</span>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-xs text-slate-500">
                    {entry.found_count}/{entry.total_ids} found
                  </span>
                  <span className="text-xs text-slate-400">
                    {timeAgo(entry.created_at)}
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
