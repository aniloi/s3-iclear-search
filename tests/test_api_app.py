"""Tests for FastAPI endpoints using TestClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from s3_search.api.app import app, store
from s3_search.api.models import SearchSessionRequest, SearchStatus
from s3_search.exceptions import AmbiguousProfileError, AuthenticationError
from s3_search.models import (
    FileMatch,
    MatchLine,
    SearchReport,
    SearchResult,
    SearchSummary,
)


@pytest.fixture(autouse=True)
def _reset_store():
    """Reset the session store before each test."""
    store._sessions.clear()
    store._history.clear()
    store._saved_searches.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# File types
# ---------------------------------------------------------------------------


def test_list_file_types(client: TestClient):
    resp = client.get("/api/file-types")
    assert resp.status_code == 200
    types = resp.json()
    assert isinstance(types, list)
    assert "fintrans" in types
    assert "all" not in types  # 'all' is excluded


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------


def test_list_profiles(client: TestClient):
    with patch("s3_search.api.app.detect_profiles", return_value=[]):
        resp = client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------


def test_initiate_search_success(client: TestClient):
    mock_session = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {"Account": "123", "Arn": "arn:test"}
    mock_session.client.return_value = mock_sts

    with patch("s3_search.api.app.validate_auth", return_value=mock_session), \
         patch("s3_search.api.app.resolve_bucket", return_value="qa.drivewealth.aod"):
        resp = client.post("/api/search", json={
            "date": "20260501",
            "ids": ["PAY-123"],
            "profile": "qa",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "search_id" in data
    assert len(data["search_id"]) == 32


def test_initiate_search_auth_failure(client: TestClient):
    with patch("s3_search.api.app.resolve_bucket", return_value="qa.drivewealth.aod"), \
         patch("s3_search.api.app.validate_auth", side_effect=AuthenticationError("qa", "Token expired")):
        resp = client.post("/api/search", json={
            "date": "20260501",
            "ids": ["PAY-123"],
            "profile": "qa",
        })

    assert resp.status_code == 401
    assert "aws sso login" in resp.json()["detail"].lower()


def test_initiate_search_ambiguous_profile(client: TestClient):
    with patch(
        "s3_search.api.app.resolve_bucket",
        side_effect=AmbiguousProfileError("qa-uat", ["qa", "uat"]),
    ):
        resp = client.post("/api/search", json={
            "date": "20260501",
            "ids": ["PAY-123"],
            "profile": "qa-uat",
        })

    assert resp.status_code == 400


def test_initiate_search_validation_error(client: TestClient):
    resp = client.post("/api/search", json={
        "date": "bad-date",
        "ids": ["PAY-123"],
        "profile": "qa",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/search/{id}/results
# ---------------------------------------------------------------------------


def test_get_results_not_found(client: TestClient):
    resp = client.get("/api/search/nonexistent/results")
    assert resp.status_code == 404


def test_get_results_not_complete(client: TestClient):
    # Create a session manually
    req = SearchSessionRequest(date="20260501", ids=["X"], profile="qa")
    session = store.create_session(
        request=req,
        resolved_bucket="qa.drivewealth.aod",
        boto3_session=None,
        identity_info={},
    )
    session.status = SearchStatus.RUNNING

    resp = client.get(f"/api/search/{session.id}/results")
    assert resp.status_code == 409


def test_get_results_completed(client: TestClient):
    req = SearchSessionRequest(date="20260501", ids=["PAY-123"], profile="qa")
    session = store.create_session(
        request=req,
        resolved_bucket="qa.drivewealth.aod",
        boto3_session=None,
        identity_info={},
    )
    session.status = SearchStatus.COMPLETED
    session.report = SearchReport(
        date="20260501",
        bucket="qa.drivewealth.aod",
        profile="qa",
        files_searched=5,
        files_failed=0,
        warnings=[],
        results=[
            SearchResult(
                id="PAY-123",
                found=True,
                file_matches=[
                    FileMatch(
                        filename="test.csv",
                        match_count=1,
                        matching_lines=[MatchLine(line_number=1, line_content="PAY-123,data")],
                    )
                ],
                total_match_count=1,
            )
        ],
        summary=SearchSummary(total_ids=1, found_count=1, not_found_count=0),
    )

    resp = client.get(f"/api/search/{session.id}/results")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["found"] == 1


# ---------------------------------------------------------------------------
# DELETE /api/search/{id} (cancel)
# ---------------------------------------------------------------------------


def test_cancel_running_search(client: TestClient):
    req = SearchSessionRequest(date="20260501", ids=["X"], profile="qa")
    session = store.create_session(
        request=req,
        resolved_bucket="qa.drivewealth.aod",
        boto3_session=None,
        identity_info={},
    )
    session.status = SearchStatus.RUNNING

    resp = client.delete(f"/api/search/{session.id}")
    assert resp.status_code == 200
    assert resp.json()["cancelled"] is True


def test_cancel_completed_search_fails(client: TestClient):
    req = SearchSessionRequest(date="20260501", ids=["X"], profile="qa")
    session = store.create_session(
        request=req,
        resolved_bucket="qa.drivewealth.aod",
        boto3_session=None,
        identity_info={},
    )
    session.status = SearchStatus.COMPLETED

    resp = client.delete(f"/api/search/{session.id}")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_empty_history(client: TestClient):
    resp = client.get("/api/search/history")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Saved searches
# ---------------------------------------------------------------------------


def test_saved_searches_crud(client: TestClient):
    # Create
    resp = client.post("/api/saved-searches", json={
        "name": "My Search",
        "params": {
            "date": "20260501",
            "ids": ["PAY-123"],
            "profile": "qa",
        },
    })
    assert resp.status_code == 200
    saved = resp.json()
    assert saved["name"] == "My Search"

    # List
    resp = client.get("/api/saved-searches")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Delete
    resp = client.delete(f"/api/saved-searches/{saved['id']}")
    assert resp.status_code == 200

    # Verify deleted
    resp = client.get("/api/saved-searches")
    assert len(resp.json()) == 0


def test_delete_nonexistent_saved_search(client: TestClient):
    resp = client.delete("/api/saved-searches/nonexistent")
    assert resp.status_code == 404
