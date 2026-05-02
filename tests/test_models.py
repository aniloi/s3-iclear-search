"""Tests for domain entities."""

from s3_search.models import (
    FileMatch,
    FileSearchResult,
    MatchLine,
    S3FileInfo,
    SearchReport,
    SearchRequest,
    SearchResult,
    SearchSummary,
)


def test_search_request_defaults():
    req = SearchRequest(
        date="20260501",
        ids=["ID1"],
        profile="qa",
        file_types=["all"],
        bucket="qa.drivewealth.aod",
    )
    assert req.output_format == "table"
    assert req.context_lines == 3
    assert req.concurrency == 10


def test_s3_file_info():
    f = S3FileInfo(key="20260501/ICLEAR_S3/file.csv", filename="file.csv", size=100)
    assert f.filename == "file.csv"
    assert f.size == 100


def test_match_line():
    ml = MatchLine(line_number=5, line_content="col1,ID123,col3")
    assert ml.line_number == 5
    assert "ID123" in ml.line_content


def test_file_search_result_no_error():
    f = S3FileInfo(key="k", filename="f.csv", size=10)
    fsr = FileSearchResult(file=f)
    assert fsr.error is None
    assert fsr.retries_used == 0
    assert fsr.matches == {}


def test_search_result_found():
    sr = SearchResult(
        id="ID1",
        found=True,
        file_matches=[FileMatch(filename="f.csv", match_count=2)],
        total_match_count=2,
    )
    assert sr.found is True
    assert sr.total_match_count == 2


def test_search_summary():
    s = SearchSummary(total_ids=4, found_count=2, not_found_count=2)
    assert s.found_count + s.not_found_count == s.total_ids
