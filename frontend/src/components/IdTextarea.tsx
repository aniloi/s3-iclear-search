/** Textarea for entering search IDs with live count display. */

import { useMemo } from "react";

interface IdTextareaProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

function countIds(raw: string): number {
  return raw
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter((s) => s && !s.startsWith("#")).length;
}

export default function IdTextarea({ value, onChange, error }: IdTextareaProps) {
  const count = useMemo(() => countIds(value), [value]);

  return (
    <div>
      <label htmlFor="search-ids" className="block text-sm font-medium text-slate-700 mb-1">
        Search IDs <span className="text-red-500">*</span>
      </label>
      <textarea
        id="search-ids"
        className={`w-full h-28 px-3 py-2 border rounded text-sm font-mono resize-y ${
          error ? "border-red-400 focus:ring-red-400" : "border-slate-300 focus:ring-blue-400"
        } focus:outline-none focus:ring-2`}
        placeholder="Enter IDs, one per line or comma-separated&#10;# Lines starting with # are comments"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid="search-ids-textarea"
        aria-describedby="ids-count"
      />
      <div className="flex justify-between mt-1">
        <span id="ids-count" className="text-xs text-slate-500">
          {count} ID{count !== 1 ? "s" : ""} detected
        </span>
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>
    </div>
  );
}
