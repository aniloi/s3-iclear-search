"""Tests for S3 file discovery and filtering."""

from unittest.mock import MagicMock

import pytest

from s3_search.discovery import VALID_FILE_TYPES, _filter_by_file_type, discover_files
from s3_search.exceptions import S3PathNotFoundError
from s3_search.models import S3FileInfo


def _make_mock_session(file_keys: list[str]) -> MagicMock:
    """Create a mock boto3 session that returns the given file keys."""
    session = MagicMock()
    s3_client = MagicMock()
    session.client.return_value = s3_client
    contents = [{"Key": key, "Size": 1000} for key in file_keys]
    paginator = MagicMock()
    paginator.paginate.return_value = [{"Contents": contents}]
    s3_client.get_paginator.return_value = paginator
    return session


def test_discover_files_normal():
    keys = [
        "20260501/ICLEAR_S3/fintrans_part1.csv",
        "20260501/ICLEAR_S3/fintrans_ira_part1.csv",
    ]
    session = _make_mock_session(keys)
    files = discover_files(session, "qa.drivewealth.aod", "20260501", ["all"])
    assert len(files) == 2


def test_discover_files_empty_raises():
    session = _make_mock_session([])
    s3_client = session.client.return_value
    paginator = MagicMock()
    paginator.paginate.return_value = [{}]
    s3_client.get_paginator.return_value = paginator
    with pytest.raises(S3PathNotFoundError):
        discover_files(session, "qa.drivewealth.aod", "20260501", ["all"])


def test_discover_files_skips_compressed():
    keys = [
        "20260501/ICLEAR_S3/file1.csv",
        "20260501/ICLEAR_S3/file2.csv.gz",
    ]
    session = _make_mock_session(keys)
    files = discover_files(session, "qa.drivewealth.aod", "20260501", ["all"])
    assert len(files) == 1
    assert files[0].filename == "file1.csv"


def test_filter_fintrans_excludes_ira():
    files = [
        S3FileInfo(key="k1", filename="fintrans_part1.csv", size=100),
        S3FileInfo(key="k2", filename="fintrans_ira_part1.csv", size=100),
    ]
    result = _filter_by_file_type(files, ["fintrans"])
    assert len(result) == 1
    assert "fintrans_ira" not in result[0].filename
