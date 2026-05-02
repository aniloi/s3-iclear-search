/** Custom hook for fetching valid file types. */

import { useEffect, useState } from "react";
import { fetchFileTypes } from "../api";

export function useFileTypes() {
  const [fileTypes, setFileTypes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchFileTypes()
      .then((data) => {
        if (!cancelled) setFileTypes(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { fileTypes, loading, error };
}
