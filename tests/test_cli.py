"""Tests for CLI argument parsing and validation."""

import sys
from unittest.mock import patch

import pytest

from s3_search.cli import _resolve_date, _resolve_ids, _validate_file_types


def test_resolve_date_valid():
    assert _resolve_date("20260501") == "20260501"


def test_resolve_date_today():
    result = _resolve_date("today")
    assert len(result) == 8
    assert result.isdigit()


def test_resolve_date_invalid_format():
    with pytest.raises(SystemExit) as exc_info:
        _resolve_date("2026-05-01")
    assert exc_info.value.code == 2


def test_resolve_date_invalid_date():
    with pytest.raises(SystemExit) as exc_info:
        _resolve_date("20261301")  # month 13
    assert exc_info.value.code == 2


def test_resolve_ids_from_comma():
    ids = _resolve_ids("ID1,ID2,ID3", None)
    assert ids == ["ID1", "ID2", "ID3"]


def test_resolve_ids_strips_whitespace():
    ids = _resolve_ids(" ID1 , ID2 ", None)
    assert ids == ["ID1", "ID2"]


def test_resolve_ids_empty_exits():
    with pytest.raises(SystemExit) as exc_info:
        _resolve_ids(",,,", None)
    assert exc_info.value.code == 2


def test_resolve_ids_from_file(tmp_path):
    id_file = tmp_path / "ids.txt"
    id_file.write_text("ID1\n# comment\n\nID2\n")
    ids = _resolve_ids(None, str(id_file))
    assert ids == ["ID1", "ID2"]


def test_resolve_ids_file_not_found():
    with pytest.raises(SystemExit) as exc_info:
        _resolve_ids(None, "/nonexistent/file.txt")
    assert exc_info.value.code == 2


def test_validate_file_types_valid():
    assert _validate_file_types("fintrans,fintrans_ira") == [
        "fintrans", "fintrans_ira"
    ]


def test_validate_file_types_all():
    assert _validate_file_types("all") == ["all"]


def test_validate_file_types_all_overrides():
    assert _validate_file_types("all,fintrans") == ["all"]


def test_validate_file_types_invalid():
    with pytest.raises(SystemExit) as exc_info:
        _validate_file_types("unknown_type")
    assert exc_info.value.code == 2
