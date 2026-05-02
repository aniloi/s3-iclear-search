/** Custom hook for search history. */

import { useCallback, useEffect, useState } from "react";
import { fetchHistory } from "../api";
import type { SearchHistoryEntry } from "../types";

export function useHistory() {
  const [history, setHistory] = useState<SearchHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    fetchHistory()
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { history, loading, refresh };
}
