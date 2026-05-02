/** Saved search presets list with save dialog. */

import { useState } from "react";
import type { SavedSearch, SearchFormData } from "../types";

interface SavedSearchesProps {
  savedSearches: SavedSearch[];
  onLoad: (params: Partial<SearchFormData>) => void;
  onDelete: (id: string) => void;
  onSave: (name: string) => void;
}

export default function SavedSearches({
  savedSearches,
  onLoad,
  onDelete,
  onSave,
}: SavedSearchesProps) {
  const [showSaveInput, setShowSaveInput] = useState(false);
  const [saveName, setSaveName] = useState("");

  const handleSave = () => {
    if (!saveName.trim()) return;
    onSave(saveName.trim());
    setSaveName("");
    setShowSaveInput(false);
  };

  return (
    <div className="p-4 border-t border-slate-200" data-testid="saved-searches">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          Saved Searches
        </h3>
        <button
          className="text-xs text-blue-600 hover:underline"
          onClick={() => setShowSaveInput(!showSaveInput)}
          data-testid="save-search-toggle"
        >
          {showSaveInput ? "Cancel" : "+ Save Current"}
        </button>
      </div>

      {showSaveInput && (
        <div className="flex gap-1 mb-2">
          <input
            type="text"
            placeholder="Name..."
            className="flex-1 px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSave()}
            data-testid="save-search-name-input"
            autoFocus
          />
          <button
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            onClick={handleSave}
            data-testid="save-search-confirm"
          >
            Save
          </button>
        </div>
      )}

      {savedSearches.length === 0 ? (
        <p className="text-xs text-slate-400">No saved searches</p>
      ) : (
        <ul className="space-y-1">
          {savedSearches.map((s) => (
            <li key={s.id} className="flex items-center justify-between group">
              <button
                className="flex-1 text-left px-2 py-1 text-xs text-slate-700 rounded hover:bg-slate-100"
                onClick={() =>
                  onLoad({
                    date: s.params.date,
                    ids: s.params.ids.join("\n"),
                    profile: s.params.profile,
                    fileTypes: s.params.file_types,
                    bucket: s.params.bucket ?? "",
                    contextLines: s.params.context_lines,
                  })
                }
                data-testid={`saved-search-load-${s.id}`}
              >
                <span className="font-medium">{s.name}</span>
                <span className="text-slate-400 ml-1">({s.params.profile})</span>
              </button>
              <button
                className="text-xs text-slate-400 hover:text-red-500 opacity-0 group-hover:opacity-100 px-1"
                onClick={() => onDelete(s.id)}
                aria-label={`Delete ${s.name}`}
                data-testid={`saved-search-delete-${s.id}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
