/** API client functions for all backend endpoints. */

import type {
  ProfileOption,
  SavedSearch,
  SearchHistoryEntry,
  SearchReportData,
} from "./types";

const BASE = "/api";

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new ApiError(resp.status, body.detail ?? resp.statusText);
  }
  return resp.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// --- Health ---

export async function healthCheck(): Promise<{ status: string }> {
  return fetchJson(`${BASE}/health`);
}

// --- Profiles ---

export async function fetchProfiles(): Promise<ProfileOption[]> {
  return fetchJson(`${BASE}/profiles`);
}

// --- File Types ---

export async function fetchFileTypes(): Promise<string[]> {
  return fetchJson(`${BASE}/file-types`);
}

// --- Search ---

export interface InitiateSearchParams {
  date: string;
  ids: string[];
  profile: string;
  file_types?: string[];
  bucket?: string | null;
  context_lines?: number;
}

export async function initiateSearch(
  params: InitiateSearchParams,
): Promise<{ search_id: string }> {
  return fetchJson(`${BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export function createSearchStream(searchId: string): EventSource {
  return new EventSource(`${BASE}/search/${searchId}/stream`);
}

export async function fetchSearchResults(
  searchId: string,
): Promise<SearchReportData> {
  return fetchJson(`${BASE}/search/${searchId}/results`);
}

export async function cancelSearch(
  searchId: string,
): Promise<{ cancelled: boolean }> {
  return fetchJson(`${BASE}/search/${searchId}`, { method: "DELETE" });
}

// --- History ---

export async function fetchHistory(): Promise<SearchHistoryEntry[]> {
  return fetchJson(`${BASE}/search/history`);
}

// --- Export ---

export function getExportUrl(searchId: string, format: "json" | "csv"): string {
  return `${BASE}/search/${searchId}/export?format=${format}`;
}

// --- Saved Searches ---

export async function fetchSavedSearches(): Promise<SavedSearch[]> {
  return fetchJson(`${BASE}/saved-searches`);
}

export async function createSavedSearch(
  name: string,
  params: InitiateSearchParams,
): Promise<SavedSearch> {
  return fetchJson(`${BASE}/saved-searches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, params }),
  });
}

export async function deleteSavedSearch(
  id: string,
): Promise<{ deleted: boolean }> {
  return fetchJson(`${BASE}/saved-searches/${id}`, { method: "DELETE" });
}
