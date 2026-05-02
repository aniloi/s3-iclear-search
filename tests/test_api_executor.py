"""Tests for the background search executor."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from s3_search.api.executor import run_search_stream
from s3_search.api.models import SearchSession, SearchSessionRequest, SearchStatus
from s3_search.api.session_store import SessionStore
from s3_search.exceptions import S3PathNotFoundError
from s3_search.models import FileSearchResult, MatchLine, S3FileInfo


def _make_session_and_store():
    """Create a test session and store."""
    store = SessionStore()
    req = SearchSessionRequest(date="20260501", ids=["PAY-123"], profile="qa")
    session = store.create_session(
        request=req,
        resolved_bucket="qa.drivewealth.aod",
        boto3_session=MagicMock(),
        identity_info={"Account": "123456", "Arn": "arn:aws:iam::user/test"},
    )
    return session, store


@pytest.mark.asyncio
async def test_stream_emits_auth_ok():
    """Test that the stream starts with an auth_ok event."""
    session, store = _make_session_and_store()

    mock_files = [S3FileInfo(key="20260501/ICLEAR_S3/test.csv", filename="test.csv", size=100)]
    mock_result = FileSearchResult(
        file=mock_files[0],
        matches={"PAY-123": [MatchLine(line_number=1, line_content="PAY-123,data")]},
        error=None,
        retries_used=0,
    )

    with patch("s3_search.api.executor.discover_files", return_value=mock_files), \
         patch("s3_search.api.executor._search_single_file", return_value=mock_result):
        events = []
        async for event in run_search_stream(session, store):
            events.append(event)

    event_types = [e["event"] for e in events]
    assert "auth_ok" in event_types
    assert event_types[0] == "auth_ok"


@pytest.mark.asyncio
async def test_stream_emits_discovery():
    """Test that discovery event is emitted with file count."""
    session, store = _make_session_and_store()

    mock_files = [
        S3FileInfo(key="20260501/ICLEAR_S3/f1.csv", filename="f1.csv", size=100),
        S3FileInfo(key="20260501/ICLEAR_S3/f2.csv", filename="f2.csv", size=200),
    ]
    mock_result = FileSearchResult(
        file=mock_files[0], matches={}, error=None, retries_used=0,
    )

    with patch("s3_search.api.executor.discover_files", return_value=mock_files), \
         patch("s3_search.api.executor._search_single_file", return_value=mock_result):
        events = []
        async for event in run_search_stream(session, store):
            events.append(event)

    discovery_events = [e for e in events if e["event"] == "discovery"]
    assert len(discovery_events) == 1
    data = json.loads(discovery_events[0]["data"])
    assert data["files_found"] == 2


@pytest.mark.asyncio
async def test_stream_emits_search_complete():
    """Test that search_complete event is emitted with report."""
    session, store = _make_session_and_store()

    mock_files = [S3FileInfo(key="20260501/ICLEAR_S3/test.csv", filename="test.csv", size=100)]
    mock_result = FileSearchResult(
        file=mock_files[0],
        matches={"PAY-123": [MatchLine(line_number=5, line_content="row,PAY-123,data")]},
        error=None,
        retries_used=0,
    )

    with patch("s3_search.api.executor.discover_files", return_value=mock_files), \
         patch("s3_search.api.executor._search_single_file", return_value=mock_result):
        events = []
        async for event in run_search_stream(session, store):
            events.append(event)

    complete_events = [e for e in events if e["event"] == "search_complete"]
    assert len(complete_events) == 1
    data = json.loads(complete_events[0]["data"])
    assert data["report"]["summary"]["found"] == 1


@pytest.mark.asyncio
async def test_stream_handles_s3_path_not_found():
    """Test that S3PathNotFoundError produces an error event."""
    session, store = _make_session_and_store()

    with patch(
        "s3_search.api.executor.discover_files",
        side_effect=S3PathNotFoundError("qa.drivewealth.aod", "20260501"),
    ):
        events = []
        async for event in run_search_stream(session, store):
            events.append(event)

    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) == 1
    assert session.status == SearchStatus.FAILED


@pytest.mark.asyncio
async def test_stream_handles_no_files():
    """Test that empty file list produces an error event."""
    session, store = _make_session_and_store()

    with patch("s3_search.api.executor.discover_files", return_value=[]):
        events = []
        async for event in run_search_stream(session, store):
            events.append(event)

    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) == 1
    data = json.loads(error_events[0]["data"])
    assert "no_files" in data["code"].lower() or "no files" in data["message"].lower()
