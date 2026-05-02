/** Global state reducer for the S3 Search UI. */

import type {
  SearchTab,
  ProfileOption,
  SearchHistoryEntry,
  SavedSearch,
  MatchLineData,
} from "../types";
import { mergeFileMatches } from "../hooks/useSearch";

export interface AppState {
  tabs: SearchTab[];
  activeTabId: string | null;
  profiles: ProfileOption[];
  fileTypes: string[];
  history: SearchHistoryEntry[];
  savedSearches: SavedSearch[];
}

export type AppAction =
  | { type: "ADD_TAB"; tab: SearchTab }
  | { type: "REMOVE_TAB"; tabId: string }
  | { type: "SET_ACTIVE_TAB"; tabId: string }
  | { type: "UPDATE_TAB"; tabId: string; updates: Partial<SearchTab> }
  | { type: "UPDATE_TAB_PROGRESS"; tabId: string; currentFile: string }
  | {
      type: "UPDATE_TAB_FILE_COMPLETE";
      tabId: string;
      filename: string;
      matches: Record<string, MatchLineData[]>;
      error: string | null;
      allIds: string[];
    }
  | { type: "SET_PROFILES"; profiles: ProfileOption[] }
  | { type: "SET_FILE_TYPES"; types: string[] }
  | { type: "ADD_HISTORY"; entry: SearchHistoryEntry }
  | { type: "SET_HISTORY"; entries: SearchHistoryEntry[] }
  | { type: "ADD_SAVED_SEARCH"; search: SavedSearch }
  | { type: "REMOVE_SAVED_SEARCH"; id: string }
  | { type: "SET_SAVED_SEARCHES"; searches: SavedSearch[] };

export const initialState: AppState = {
  tabs: [],
  activeTabId: null,
  profiles: [],
  fileTypes: [],
  history: [],
  savedSearches: [],
};

function updateTab(
  tabs: SearchTab[],
  tabId: string,
  updater: (tab: SearchTab) => SearchTab,
): SearchTab[] {
  return tabs.map((t) => (t.id === tabId ? updater(t) : t));
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "ADD_TAB":
      return { ...state, tabs: [...state.tabs, action.tab] };

    case "REMOVE_TAB": {
      const remaining = state.tabs.filter((t) => t.id !== action.tabId);
      let activeTabId = state.activeTabId;
      if (activeTabId === action.tabId) {
        activeTabId = remaining.length > 0 ? remaining[remaining.length - 1].id : null;
      }
      return { ...state, tabs: remaining, activeTabId };
    }

    case "SET_ACTIVE_TAB":
      return { ...state, activeTabId: action.tabId };

    case "UPDATE_TAB":
      return {
        ...state,
        tabs: updateTab(state.tabs, action.tabId, (t) => ({
          ...t,
          ...action.updates,
        })),
      };

    case "UPDATE_TAB_PROGRESS":
      return {
        ...state,
        tabs: updateTab(state.tabs, action.tabId, (t) => ({
          ...t,
          fileProgress: { ...t.fileProgress, currentFile: action.currentFile },
        })),
      };

    case "UPDATE_TAB_FILE_COMPLETE": {
      return {
        ...state,
        tabs: updateTab(state.tabs, action.tabId, (t) => {
          const completed = t.fileProgress.completed + 1;
          const total = t.fileProgress.total;
          const warnings = action.error
            ? [...t.warnings, action.error]
            : t.warnings;
          return {
            ...t,
            fileProgress: {
              ...t.fileProgress,
              completed,
              percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
              currentFile: null,
            },
            results: mergeFileMatches(
              t.results,
              action.allIds,
              action.matches,
              action.filename,
            ),
            warnings,
          };
        }),
      };
    }

    case "SET_PROFILES":
      return { ...state, profiles: action.profiles };

    case "SET_FILE_TYPES":
      return { ...state, fileTypes: action.types };

    case "ADD_HISTORY":
      return { ...state, history: [action.entry, ...state.history] };

    case "SET_HISTORY":
      return { ...state, history: action.entries };

    case "ADD_SAVED_SEARCH":
      return {
        ...state,
        savedSearches: [...state.savedSearches, action.search],
      };

    case "REMOVE_SAVED_SEARCH":
      return {
        ...state,
        savedSearches: state.savedSearches.filter((s) => s.id !== action.id),
      };

    case "SET_SAVED_SEARCHES":
      return { ...state, savedSearches: action.searches };

    default:
      return state;
  }
}
