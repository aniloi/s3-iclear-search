/** Custom hook for saved search presets. */

import { useCallback, useEffect, useState } from "react";
import {
  fetchSavedSearches,
  createSavedSearch,
  deleteSavedSearch,
  type InitiateSearchParams,
} from "../api";
import type { SavedSearch } from "../types";

export function useSavedSearches() {
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    fetchSavedSearches()
      .then(setSavedSearches)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const save = useCallback(
    async (name: string, params: InitiateSearchParams) => {
      const saved = await createSavedSearch(name, params);
      setSavedSearches((prev) => [...prev, saved]);
      return saved;
    },
    [],
  );

  const remove = useCallback(async (id: string) => {
    await deleteSavedSearch(id);
    setSavedSearches((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { savedSearches, loading, save, remove, refresh };
}
