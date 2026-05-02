"""Thread-safe in-memory store for search sessions."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from s3_search.api.models import (
    SavedSearchCreate,
    SavedSearchResponse,
    SearchHistoryEntry,
    SearchSession,
    SearchSessionRequest,
    SearchStatus,
)


class SessionStore:
    """In-memory store for all search sessions, history, and saved searches.

    Thread-safe: all mutations are protected by a lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, SearchSession] = {}
        self._history: list[SearchHistoryEntry] = []
        self._saved_searches: list[SavedSearchResponse] = []

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(
        self,
        request: SearchSessionRequest,
        resolved_bucket: str,
        boto3_session: Any,
        identity_info: dict[str, str],
    ) -> SearchSession:
        """Create and store a new search session."""
        session = SearchSession(
            request=request,
            resolved_bucket=resolved_bucket,
            boto3_session=boto3_session,
            identity_info=identity_info,
        )
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get_session(self, search_id: str) -> SearchSession | None:
        """Retrieve a session by ID."""
        with self._lock:
            return self._sessions.get(search_id)

    def cancel_session(self, search_id: str) -> bool:
        """Signal cancellation for a session. Returns True if cancelled."""
        with self._lock:
            session = self._sessions.get(search_id)
            if session is None:
                return False
            if session.status not in (SearchStatus.PENDING, SearchStatus.RUNNING):
                return False
            session.cancelled.set()
            session.status = SearchStatus.CANCELLED
            session.completed_at = datetime.now(timezone.utc)
            return True

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def add_to_history(self, session: SearchSession) -> None:
        """Add a completed/cancelled/failed session to history."""
        entry = session.to_history_entry()
        with self._lock:
            self._history.insert(0, entry)

    def get_history(self) -> list[SearchHistoryEntry]:
        """Return history ordered by most recent first."""
        with self._lock:
            return list(self._history)

    # ------------------------------------------------------------------
    # Saved Searches
    # ------------------------------------------------------------------

    def save_search(self, data: SavedSearchCreate) -> SavedSearchResponse:
        """Save a search parameter preset."""
        saved = SavedSearchResponse(
            id=uuid.uuid4().hex,
            name=data.name,
            params=data.params,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._saved_searches.append(saved)
        return saved

    def get_saved_searches(self) -> list[SavedSearchResponse]:
        """Return all saved searches."""
        with self._lock:
            return list(self._saved_searches)

    def delete_saved_search(self, saved_id: str) -> bool:
        """Delete a saved search by ID. Returns True if found and deleted."""
        with self._lock:
            for i, s in enumerate(self._saved_searches):
                if s.id == saved_id:
                    self._saved_searches.pop(i)
                    return True
        return False
