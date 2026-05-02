"""Shared pytest fixtures for S3 search tool tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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


@pytest.fixture
def sample_request() -> SearchRequest:
    """A typical search request for testing."""
    return SearchRequest(
        date="20260501",
        ids=["FABZ003185-1777650549569-RRKJF", "DWTU000481"],
        profile="qa",
        file_types=["all"],
        bucket="qa.drivewealth.aod",
        output_format="table",
        context_lines=3,
    )


@pytest.fixture
def sample_files() -> list[S3FileInfo]:
    """Sample S3 file list for testing."""
    return [
        S3FileInfo(
            key="20260501/ICLEAR_S3/DRVW_INTE_transactions_fintrans_202605010700-202605010715_part1.csv",
            filename="DRVW_INTE_transactions_fintrans_202605010700-202605010715_part1.csv",
            size=1400000,
        ),
        S3FileInfo(
            key="20260501/ICLEAR_S3/DRVW_INTE_transactions_fintrans_ira_202605010700-202605010715_part1.csv",
            filename="DRVW_INTE_transactions_fintrans_ira_202605010700-202605010715_part1.csv",
            size=500000,
        ),
    ]


@pytest.fixture
def sample_report() -> SearchReport:
    """A sample search report for renderer testing."""
    return SearchReport(
        date="20260501",
        bucket="qa.drivewealth.aod",
        profile="qa",
        files_searched=131,
        files_failed=0,
        warnings=[],
        results=[
            SearchResult(
                id="FABZ003185-1777650549569-RRKJF",
                found=True,
                file_matches=[
                    FileMatch(
                        filename="fintrans_ira_part1.csv",
                        match_count=1,
                        matching_lines=[
                            MatchLine(line_number=42, line_content="col1,FABZ003185-1777650549569-RRKJF,col3")
                        ],
                    )
                ],
                total_match_count=1,
            ),
            SearchResult(
                id="DWTU000481",
                found=False,
                file_matches=[],
                total_match_count=0,
            ),
        ],
        summary=SearchSummary(total_ids=2, found_count=1, not_found_count=1),
    )


@pytest.fixture
def mock_session() -> MagicMock:
    """A mock boto3 session."""
    session = MagicMock()
    return session
