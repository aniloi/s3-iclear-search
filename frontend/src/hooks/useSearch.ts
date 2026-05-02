/** Custom hook for search lifecycle: POST + SSE streaming. */

import { useCallback } from "react";
import { initiateSearch, createSearchStream, cancelSearch, type InitiateSearchParams } from "../api";
import { useAppDispatch } from "../state/AppContext";
import type { SearchFormData, SearchResultData, MatchLineData } from "../types";

function parseIds(raw: string): string[] {
  return raw
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter((s) => s && !s.startsWith("#"));
}

/** Merge file_complete matches into the running results array. */
function mergeFileMatches(
  existing: SearchResultData[],
  allIds: string[],
  fileMatches: Record<string, MatchLineData[]>,
  filename: string,
): SearchResultData[] {
  const updated = [...existing];
  const byId = new Map(updated.map((r) => [r.id, r]));

  for (const id of allIds) {
    const lines = fileMatches[id];
    if (!lines || lines.length === 0) continue;

    let entry = byId.get(id);
    if (!entry) {
      entry = { id, found: true, totalMatchCount: 0, files: [] };
      updated.push(entry);
      byId.set(id, entry);
    }
    entry.found = true;
    entry.totalMatchCount += lines.length;
    entry.files = [
      ...entry.files,
      {
        filename,
        matchCount: lines.length,
        context: lines.map((l) => l.line_content),
      },
    ];
  }

  return updated;
}

export function useSearch() {
  const dispatch = useAppDispatch();

  const startSearch = useCallback(
    async (params: SearchFormData) => {
      const ids = parseIds(params.ids);
      const apiParams: InitiateSearchParams = {
        date: params.date,
        ids,
        profile: params.profile,
        file_types: params.fileTypes.length > 0 ? params.fileTypes : ["all"],
        bucket: params.bucket || null,
        context_lines: params.contextLines,
      };

      // Initiate search (sync auth)
      const { search_id } = await initiateSearch(apiParams);

      // Create tab
      const tab = {
        id: search_id,
        label: `${params.date} / ${params.profile}`,
        status: "connecting" as const,
        params,
        authInfo: null,
        discovery: null,
        fileProgress: { total: 0, completed: 0, currentFile: null, percentage: 0 },
        results: [] as SearchResultData[],
        report: null,
        warnings: [] as string[],
        error: null,
      };

      dispatch({ type: "ADD_TAB", tab });
      dispatch({ type: "SET_ACTIVE_TAB", tabId: search_id });

      // Open SSE stream
      const es = createSearchStream(search_id);

      es.addEventListener("auth_ok", (e) => {
        const data = JSON.parse(e.data);
        dispatch({
          type: "UPDATE_TAB",
          tabId: search_id,
          updates: { status: "discovering", authInfo: data },
        });
      });

      es.addEventListener("discovery", (e) => {
        const data = JSON.parse(e.data);
        dispatch({
          type: "UPDATE_TAB",
          tabId: search_id,
          updates: {
            status: "searching",
            discovery: data,
            fileProgress: {
              total: data.files_found,
              completed: 0,
              currentFile: null,
              percentage: 0,
            },
          },
        });
      });

      es.addEventListener("file_start", (e) => {
        const data = JSON.parse(e.data);
        dispatch({
          type: "UPDATE_TAB_PROGRESS",
          tabId: search_id,
          currentFile: data.filename,
        });
      });

      es.addEventListener("file_complete", (e) => {
        const data = JSON.parse(e.data);
        dispatch({
          type: "UPDATE_TAB_FILE_COMPLETE",
          tabId: search_id,
          filename: data.filename,
          matches: data.matches,
          error: data.error,
          allIds: ids,
        });
      });

      es.addEventListener("search_complete", (e) => {
        const data = JSON.parse(e.data);
        dispatch({
          type: "UPDATE_TAB",
          tabId: search_id,
          updates: { status: "complete", report: data.report },
        });
        es.close();
      });

      es.addEventListener("cancelled", () => {
        dispatch({
          type: "UPDATE_TAB",
          tabId: search_id,
          updates: { status: "cancelled" },
        });
        es.close();
      });

      es.addEventListener("error", (e) => {
        if (e instanceof MessageEvent) {
          const data = JSON.parse(e.data);
          dispatch({
            type: "UPDATE_TAB",
            tabId: search_id,
            updates: { status: "error", error: data.message },
          });
        } else {
          dispatch({
            type: "UPDATE_TAB",
            tabId: search_id,
            updates: { status: "error", error: "Connection lost" },
          });
        }
        es.close();
      });

      es.onerror = () => {
        // EventSource native error — connection lost
        if (es.readyState === EventSource.CLOSED) return;
        dispatch({
          type: "UPDATE_TAB",
          tabId: search_id,
          updates: { status: "error", error: "SSE connection lost" },
        });
        es.close();
      };

      return search_id;
    },
    [dispatch],
  );

  const cancel = useCallback(
    async (searchId: string) => {
      await cancelSearch(searchId);
    },
    [],
  );

  return { startSearch, cancelSearch: cancel };
}

export { parseIds, mergeFileMatches };
