/** Collapsible warnings banner for file-level errors. */

import { useState } from "react";

interface WarningsBannerProps {
  warnings: string[];
}

export default function WarningsBanner({ warnings }: WarningsBannerProps) {
  const [expanded, setExpanded] = useState(false);

  if (warnings.length === 0) return null;

  return (
    <div className="mb-4 border border-amber-300 bg-amber-50 rounded" data-testid="warnings-banner">
      <button
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-amber-800"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        data-testid="warnings-toggle"
      >
        <span>⚠️ {warnings.length} warning{warnings.length !== 1 ? "s" : ""}</span>
        <span>{expanded ? "▾" : "▸"}</span>
      </button>
      {expanded && (
        <ul className="px-4 pb-3 space-y-1">
          {warnings.map((w, i) => (
            <li key={i} className="text-xs text-amber-700 font-mono">
              {w}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
