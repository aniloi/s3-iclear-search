"""Tests for parallel search engine."""

import io
from unittest.mock import MagicMock, patch

from s3_search.models import S3FileInfo, SearchRequest
from s3_search.search import _search_single_file, aggregate_results, search_files


def _make_streaming_body(content: str) -> MagicMock:
    """Create a mock S3 streaming body from string content."""
    body = io.BytesIO(content.encode("utf-8"))
    body.close = MagicMock()  # prevent actual close
    return body


def test_search_single_file_finds_match():
    session = MagicMock()
    s3_client = MagicMock()
    session.client.return_value = s3_client

    csv_content = "col1,col2,col3\nrow1,TESTID123,data\nrow2,other,data\n"
    s3_client.get_object.return_value = {"Body": _make_streaming_body(csv_content)}

    file_info = S3FileInfo(key="k", filename="test.csv", size=100)
    result = _search_single_file(session, "bucket", ["TESTID123"], file_info)

    assert result.error is None
    assert "TESTID123" in result.matches
    assert len(result.matches["TESTID123"]) == 1
    assert result.matches["TESTID123"][0].line_number == 2


def test_search_single_file_no_match():
    session = MagicMock()
    s3_client = MagicMock()
    session.client.return_value = s3_client

    csv_content = "col1,col2,col3\nrow1,data1,data2\n"
    s3_client.get_object.return_value = {"Body": _make_streaming_body(csv_content)}

    file_info = S3FileInfo(key="k", filename="test.csv", size=100)
    result = _search_single_file(session, "bucket", ["NOTFOUND"], file_info)

    assert result.error is None
    assert len(result.matches) == 0


def test_search_single_file_multiple_ids():
    session = MagicMock()
    s3_client = MagicMock()
    session.client.return_value = s3_client

    csv_content = "ID1,data\nID2,data\nID1,more\n"
    s3_client.get_object.return_value = {"Body": _make_streaming_body(csv_content)}

    file_info = S3FileInfo(key="k", filename="test.csv", size=100)
    result = _search_single_file(session, "bucket", ["ID1", "ID2"], file_info)

    assert len(result.matches["ID1"]) == 2
    assert len(result.matches["ID2"]) == 1
