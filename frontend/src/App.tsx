/** Root application component. */

import { useCallback, useEffect, useState } from "react";
import { AppProvider, useAppState, useAppDispatch } from "./state/AppContext";
import { useSearch } from "./hooks/useSearch";
import { useProfiles } from "./hooks/useProfiles";
import { useFileTypes } from "./hooks/useFileTypes";
import { useHistory } from "./hooks/useHistory";
import { useSavedSearches } from "./hooks/useSavedSearches";
import { fetchSearchResults, ApiError, type InitiateSearchParams } from "./api";
import type { SearchFormData, SearchReportData } from "./types";

import AppLayout from "./components/AppLayout";
import Header from "./components/Header";
import TabBar from "./components/TabBar";
import Sidebar from "./components/Sidebar";
import SearchForm from "./components/SearchForm";
import SavedSearches from "./components/SavedSearches";
import HistoryPanel from "./components/HistoryPanel";
import EmptyState from "./components/EmptyState";
import SearchProgress from "./components/SearchProgress";
import ResultsView from "./components/ResultsView";

function AppContent() {
  const state = useAppState();
  const dispatch = useAppDispatch();
  const { startSearch, cancelSearch } = useSearch();
  const { profiles } = useProfiles();
  const { fileTypes } = useFileTypes();
  const { history, refresh: refreshHistory } = useHistory();
  const { savedSearches, save: saveSearch, remove: removeSavedSearch } = useSavedSearches();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formInitial, setFormInitial] = useState<Partial<SearchFormData> | undefined>();

  // Sync reference data into global state
  useEffect(() => {
    dispatch({ type: "SET_PROFILES", profiles });
  }, [profiles, dispatch]);

  useEffect(() => {
    dispatch({ type: "SET_FILE_TYPES", types: fileTypes });
  }, [fileTypes, dispatch]);

  useEffect(() => {
    dispatch({ type: "SET_HISTORY", entries: history });
  }, [history, dispatch]);

  // Refresh history when a tab completes
  useEffect(() => {
    const completedCount = state.tabs.filter(
      (t) => t.status === "complete" || t.status === "cancelled",
    ).length;
    if (completedCount > 0) refreshHistory();
  }, [state.tabs, refreshHistory]);

  const handleSubmit = useCallback(
    async (params: SearchFormData) => {
      setIsSubmitting(true);
      setFormError(null);
      try {
        await startSearch(params);
      } catch (err) {
        if (err instanceof ApiError) {
          setFormError(err.message);
        } else {
          setFormError("An unexpected error occurred");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [startSearch],
  );

  const handleCancel = useCallback(
    async (searchId: string) => {
      try {
        await cancelSearch(searchId);
      } catch {
        // Ignore cancel errors
      }
    },
    [cancelSearch],
  );

  const handleReopenHistory = useCallback(
    async (searchId: string) => {
      try {
        const report: SearchReportData = await fetchSearchResults(searchId);
        const tab = {
          id: searchId + "-reopened-" + Date.now(),
          label: `${report.date} / ${report.profile}`,
          status: "complete" as const,
          params: { date: report.date, ids: "", profile: report.profile, fileTypes: [], bucket: "", contextLines: 3 },
          authInfo: null,
          discovery: null,
          fileProgress: { total: 0, completed: 0, currentFile: null, percentage: 100 },
          results: report.results,
          report,
          warnings: report.warnings,
          error: null,
        };
        dispatch({ type: "ADD_TAB", tab });
        dispatch({ type: "SET_ACTIVE_TAB", tabId: tab.id });
      } catch {
        // Session may have been lost on server restart
      }
    },
    [dispatch],
  );

  const handleSaveSearch = useCallback(
    async (name: string) => {
      // Save current form state — we use a minimal params object
      const params: InitiateSearchParams = {
        date: "",
        ids: [],
        profile: "",
      };
      try {
        await saveSearch(name, params);
      } catch {
        // Ignore save errors
      }
    },
    [saveSearch],
  );

  const activeTab = state.tabs.find((t) => t.id === state.activeTabId) ?? null;

  return (
    <AppLayout
      header={<Header />}
      tabBar={
        <TabBar
          tabs={state.tabs}
          activeTabId={state.activeTabId}
          onSelectTab={(id) => dispatch({ type: "SET_ACTIVE_TAB", tabId: id })}
          onCloseTab={(id) => dispatch({ type: "REMOVE_TAB", tabId: id })}
        />
      }
      sidebar={
        <Sidebar>
          <SearchForm
            profiles={profiles}
            fileTypes={fileTypes}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            initialValues={formInitial}
          />
          {formError && (
            <div className="mx-4 mb-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700" data-testid="form-error">
              {formError}
            </div>
          )}
          <SavedSearches
            savedSearches={savedSearches}
            onLoad={(params) => setFormInitial(params)}
            onDelete={removeSavedSearch}
            onSave={handleSaveSearch}
          />
          <HistoryPanel history={history} onReopen={handleReopenHistory} />
        </Sidebar>
      }
    >
      {activeTab ? (
        activeTab.status === "complete" || activeTab.status === "cancelled" ? (
          <ResultsView tab={activeTab} />
        ) : activeTab.status === "error" ? (
          <div className="p-6" data-testid="error-view">
            <div className="bg-red-50 border border-red-200 rounded p-4">
              <h3 className="text-red-800 font-medium mb-2">Search Error</h3>
              <p className="text-sm text-red-700">{activeTab.error}</p>
              {activeTab.error?.includes("aws sso login") && (
                <pre className="mt-2 p-2 bg-white rounded border text-xs font-mono">
                  aws sso login --profile {activeTab.params.profile}
                </pre>
              )}
            </div>
          </div>
        ) : (
          <SearchProgress tab={activeTab} onCancel={() => handleCancel(activeTab.id)} />
        )
      ) : (
        <EmptyState />
      )}
    </AppLayout>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
