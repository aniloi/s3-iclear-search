"""Tests for API Pydantic models and SessionStore."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from s3_search.api.models import (
    SavedSearchCreate,
    SearchSession,
    SearchSessionRequest,
    SearchStatus,
)
from s3_search.api.session_store import SessionStore


# ---------------------------------------------------------------------------
# SearchSessionRequest validation
# ---------------------------------------------------------------------------


class TestSearchSessionRequest:
    """Tests for SearchSessionRequest Pydantic model."""

    def test_valid_request(self):
        req = SearchSessionRequest(
            date="20260501",
            ids=["PAY-123", "ACC-456"],
            profile="qa",
        )
        assert req.date == "20260501"
        assert req.ids == ["PAY-123", "ACC-456"]
        assert req.profile == "qa"
        assert req.file_types == ["all"]
        assert req.bucket is None
        assert req.context_lines == 3

    def test_today_date(self):
        req = SearchSessionRequest(date="today", ids=["X"], profile="qa")
        assert req.date == "today"

    def test_invalid_date_format(self):
        with pytest.raises(ValidationError, match="YYYYMMDD"):
            SearchSessionRequest(date="2026-05-01", ids=["X"], profile="qa")

    def test_invalid_date_short(self):
        with pytest.raises(ValidationError, match="YYYYMMDD"):
            SearchSessionRequest(date="202605", ids=["X"], profile="qa")

    def test_invalid_calendar_date(self):
        with pytest.raises(ValidationError, match="not a valid calendar date"):
            SearchSessionRequest(date="20261301", ids=["X"], profile="qa")

    def test_empty_ids_rejected(self):
        with pytest.raises(ValidationError, match="at least one"):
            SearchSessionRequest(date="20260501", ids=["", "  "], profile="qa")

    def test_ids_whitespace_stripped(self):
        req = SearchSessionRequest(date="20260501", ids=["  PAY-123  "], profile="qa")
        assert req.ids == ["PAY-123"]

    def test_empty_profile_rejected(self):
        with pytest.raises(ValidationError):
            SearchSessionRequest(date="20260501", ids=["X"], profile="")

    def test_invalid_file_type(self):
        with pytest.raises(ValidationError, match="Unknown file type"):
            SearchSessionRequest(
                date="20260501", ids=["X"], profile="qa", file_types=["bogus"]
            )

    def test_valid_file_types(self):
        req = SearchSessionRequest(
            date="20260501",
            ids=["X"],
            profile="qa",
            file_types=["fintrans", "ordertrans"],
        )
        assert req.file_types == ["fintrans", "ordertrans"]

    def test_negative_context_lines_rejected(self):
        with pytest.raises(ValidationError):
            SearchSessionRequest(
                date="20260501", ids=["X"], profile="qa", context_lines=-1
            )

    def test_bucket_override(self):
        req = SearchSessionRequest(
            date="20260501", ids=["X"], profile="qa", bucket="custom-bucket"
        )
        assert req.bucket == "custom-bucket"


# ---------------------------------------------------------------------------
# SearchSession
# ---------------------------------------------------------------------------


class TestSearchSession:
    """Tests for SearchSession internal model."""

    def _make_session(self) -> SearchSession:
        req = SearchSessionRequest(date="20260501", ids=["PAY-123"], profile="qa")
        return SearchSession(
            request=req,
            resolved_bucket="qa.drivewealth.aod",
            boto3_session=None,
            identity_info={"Account": "123456", "Arn": "arn:aws:iam::user/test"},
        )

    def test_session_has_uuid(self):
        session = self._make_session()
        assert len(session.id) == 32  # hex UUID without dashes

    def test_session_initial_status(self):
        session = self._make_session()
        assert session.status == SearchStatus.PENDING

    def test_session_to_history_entry(self):
        session = self._make_session()
        entry = session.to_history_entry()
        assert entry.search_id == session.id
        assert entry.date == "20260501"
        assert entry.profile == "qa"
        assert entry.status == SearchStatus.PENDING


# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------


class TestSessionStore:
    """Tests for SessionStore thread-safe store."""

    def _make_store_with_session(self):
        store = SessionStore()
        req = SearchSessionRequest(date="20260501", ids=["PAY-123"], profile="qa")
        session = store.create_session(
            request=req,
            resolved_bucket="qa.drivewealth.aod",
            boto3_session=None,
            identity_info={"Account": "123456", "Arn": "arn:aws:iam::user/test"},
        )
        return store, session

    def test_create_and_get_session(self):
        store, session = self._make_store_with_session()
        retrieved = store.get_session(session.id)
        assert retrieved is session

    def test_get_nonexistent_session(self):
        store = SessionStore()
        assert store.get_session("nonexistent") is None

    def test_cancel_running_session(self):
        store, session = self._make_store_with_session()
        session.status = SearchStatus.RUNNING
        assert store.cancel_session(session.id) is True
        assert session.status == SearchStatus.CANCELLED
        assert session.cancelled.is_set()

    def test_cancel_completed_session_fails(self):
        store, session = self._make_store_with_session()
        session.status = SearchStatus.COMPLETED
        assert store.cancel_session(session.id) is False

    def test_cancel_nonexistent_session_fails(self):
        store = SessionStore()
        assert store.cancel_session("nonexistent") is False

    def test_history(self):
        store, session = self._make_store_with_session()
        store.add_to_history(session)
        history = store.get_history()
        assert len(history) == 1
        assert history[0].search_id == session.id

    def test_saved_searches_crud(self):
        store = SessionStore()
        req = SearchSessionRequest(date="20260501", ids=["X"], profile="qa")
        data = SavedSearchCreate(name="My Search", params=req)

        saved = store.save_search(data)
        assert saved.name == "My Search"
        assert len(store.get_saved_searches()) == 1

        assert store.delete_saved_search(saved.id) is True
        assert len(store.get_saved_searches()) == 0

    def test_delete_nonexistent_saved_search(self):
        store = SessionStore()
        assert store.delete_saved_search("nonexistent") is False
