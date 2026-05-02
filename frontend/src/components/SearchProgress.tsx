/** Progress display during search: steps + progress bar + cancel. */

import type { SearchTab } from "../types";

interface SearchProgressProps {
  tab: SearchTab;
  onCancel: () => void;
}

const STEPS = ["Authenticating", "Discovering files", "Searching", "Complete"] as const;

function stepIndex(status: SearchTab["status"]): number {
  switch (status) {
    case "connecting":
    case "authenticating":
      return 0;
    case "discovering":
      return 1;
    case "searching":
      return 2;
    case "complete":
      return 3;
    default:
      return -1;
  }
}

export default function SearchProgress({ tab, onCancel }: SearchProgressProps) {
  const current = stepIndex(tab.status);
  const { completed, total, percentage, currentFile } = tab.fileProgress;

  return (
    <div className="space-y-6" data-testid="search-progress">
      {/* Step indicators */}
      <div className="flex items-center gap-2">
        {STEPS.map((step, i) => (
          <div key={step} className="flex items-center gap-2">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                i < current
                  ? "bg-green-500 text-white"
                  : i === current
                    ? "bg-blue-500 text-white animate-pulse"
                    : "bg-slate-200 text-slate-500"
              }`}
            >
              {i < current ? "✓" : i + 1}
            </div>
            <span
              className={`text-sm ${
                i === current ? "text-blue-700 font-medium" : "text-slate-500"
              }`}
            >
              {step}
            </span>
            {i < STEPS.length - 1 && <div className="w-8 h-px bg-slate-300" />}
          </div>
        ))}
      </div>

      {/* Progress bar (visible during searching) */}
      {tab.status === "searching" && total > 0 && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-slate-600">
            <span>
              {completed}/{total} files ({percentage}%)
            </span>
            {currentFile && (
              <span className="text-xs text-slate-400 truncate max-w-[300px]">
                {currentFile}
              </span>
            )}
          </div>
          <div className="w-full bg-slate-200 rounded-full h-2.5">
            <div
              className="bg-blue-500 h-2.5 rounded-full transition-all duration-300"
              style={{ width: `${percentage}%` }}
              role="progressbar"
              aria-valuenow={percentage}
              aria-valuemin={0}
              aria-valuemax={100}
              data-testid="progress-bar"
            />
          </div>
        </div>
      )}

      {/* Cancel button */}
      {(tab.status === "searching" || tab.status === "discovering") && (
        <button
          className="px-4 py-1.5 text-sm border border-red-300 text-red-600 rounded hover:bg-red-50 transition-colors"
          onClick={onCancel}
          data-testid="cancel-search-button"
        >
          Cancel Search
        </button>
      )}
    </div>
  );
}
