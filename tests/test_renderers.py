"""Tests for output renderers."""

import json

from s3_search.renderers import render_report


def test_table_output(sample_report, capsys):
    render_report(sample_report, "table", context_lines=3)
    captured = capsys.readouterr()
    assert "20260501" in captured.out
    assert "qa.drivewealth.aod" in captured.out
    assert "FABZ003185" in captured.out
    assert "DWTU000481" in captured.out
    assert "1/2 IDs found" in captured.out


def test_json_output(sample_report, capsys):
    render_report(sample_report, "json", context_lines=3)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["date"] == "20260501"
    assert data["filesSearched"] == 131
    assert len(data["results"]) == 2
    assert data["summary"]["found"] == 1
    assert data["summary"]["notFound"] == 1


def test_csv_output(sample_report, capsys):
    render_report(sample_report, "csv", context_lines=3)
    captured = capsys.readouterr()
    lines = [line.rstrip("\r") for line in captured.out.strip().split("\n")]
    assert lines[0] == "id,found,filename,matchCount,context"
    assert len(lines) == 3  # header + 1 found + 1 not found


def test_table_no_context(sample_report, capsys):
    render_report(sample_report, "table", context_lines=0)
    captured = capsys.readouterr()
    assert "Line 42:" not in captured.out


def test_json_no_context(sample_report, capsys):
    render_report(sample_report, "json", context_lines=0)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    for result in data["results"]:
        for f in result["files"]:
            assert f["context"] == []
