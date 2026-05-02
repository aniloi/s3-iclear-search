/** Tab bar for switching between search result tabs. */

import type { SearchTab } from "../types";

interface TabBarProps {
  tabs: SearchTab[];
  activeTabId: string | null;
  onSelectTab: (tabId: string) => void;
  onCloseTab: (tabId: string) => void;
}

function statusIcon(status: SearchTab["status"]): string {
  switch (status) {
    case "connecting":
    case "authenticating":
    case "discovering":
    case "searching":
      return "⏳";
    case "complete":
      return "✅";
    case "cancelled":
      return "⏹";
    case "error":
      return "⚠️";
    default:
      return "";
  }
}

export default function TabBar({ tabs, activeTabId, onSelectTab, onCloseTab }: TabBarProps) {
  if (tabs.length === 0) return null;

  return (
    <div className="flex items-center gap-1 bg-slate-700 px-4 py-1 overflow-x-auto" data-testid="tab-bar">
      {tabs.map((tab) => (
        <div
          key={tab.id}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-t text-sm cursor-pointer select-none ${
            tab.id === activeTabId
              ? "bg-white text-slate-800 font-medium"
              : "bg-slate-600 text-slate-200 hover:bg-slate-500"
          }`}
          data-testid={`tab-${tab.id}`}
        >
          <button
            className="flex items-center gap-1"
            onClick={() => onSelectTab(tab.id)}
            aria-label={`Switch to ${tab.label}`}
            data-testid={`tab-select-${tab.id}`}
          >
            <span>{statusIcon(tab.status)}</span>
            <span className="max-w-[160px] truncate">{tab.label}</span>
          </button>
          <button
            className="ml-1 text-xs opacity-60 hover:opacity-100"
            onClick={(e) => {
              e.stopPropagation();
              onCloseTab(tab.id);
            }}
            aria-label={`Close ${tab.label}`}
            data-testid={`tab-close-${tab.id}`}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
