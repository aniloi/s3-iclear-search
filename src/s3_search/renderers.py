"""Output renderers for search results (table, JSON, CSV)."""

from __future__ import annotations

import csv
import io
import json
import sys

from s3_search.models import SearchReport


# ANSI color codes
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


def _use_color() -> bool:
    """Return True if stdout is a TTY and supports color."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _colorize(text: str, color: str) -> str:
    """Wrap text in ANSI color codes if color output is enabled."""
    if _use_color():
        return f"{color}{text}{_RESET}"
    return text


def render_report(report: SearchReport, output_format: str, context_lines: int) -> None:
    """Render the search report to stdout in the specified format.

    Args:
        report: The search report to render.
        output_format: One of 'table', 'json', 'csv'.
        context_lines: Number of context lines to display (0 to suppress).
    """
    if output_format == "json":
        _render_json(report, context_lines)
    elif output_format == "csv":
        _render_csv(report, context_lines)
    else:
        _render_table(report, context_lines)


def _render_table(report: SearchReport, context_lines: int) -> None:
    """Render results as a formatted table with optional ANSI colors."""
    print(f"Search Results for date: {report.date}")
    print(f"Bucket: {report.bucket}")
    print(f"Profile: {report.profile}")
    print(f"Files searched: {report.files_searched}")
    if report.files_failed > 0:
        print(f"Files failed: {report.files_failed}")
    print()

    # Print warnings
    for warning in report.warnings:
        print(_colorize(f"⚠  {warning}", _YELLOW))
    if report.warnings:
        print()

    # Calculate column widths
    id_width = max(
        (len(r.id) for r in report.results),
        default=2,
    )
    id_width = max(id_width, 2)  # minimum width for "ID" header

    # Print table header
    header = f"{'ID':<{id_width}} | Found | File(s)"
    print(header)
    print("-" * id_width + "-|-------|" + "-" * 40)

    # Print results
    for result in report.results:
        if result.found:
            indicator = _colorize("✅", _GREEN)
            filenames = ", ".join(fm.filename for fm in result.file_matches)
            print(f"{result.id:<{id_width}} | {indicator}    | {filenames}")
            if context_lines > 0:
                for fm in result.file_matches:
                    lines_to_show = fm.matching_lines[:context_lines] if context_lines > 0 else []
                    for ml in lines_to_show:
                        print(f"  Line {ml.line_number}: {ml.line_content}")
                    remaining = len(fm.matching_lines) - len(lines_to_show)
                    if remaining > 0:
                        print(f"  ... +{remaining} more matches in {fm.filename}")
        else:
            indicator = _colorize("❌", _RED)
            print(f"{result.id:<{id_width}} | {indicator}    | —")

    # Print summary
    print()
    print(
        f"Summary: {report.summary.found_count}/{report.summary.total_ids} IDs found"
    )


def _render_json(report: SearchReport, context_lines: int) -> None:
    """Render results as structured JSON."""
    output = {
        "date": report.date,
        "bucket": report.bucket,
        "profile": report.profile,
        "filesSearched": report.files_searched,
        "filesFailed": report.files_failed,
        "warnings": report.warnings,
        "results": [
            {
                "id": result.id,
                "found": result.found,
                "totalMatchCount": result.total_match_count,
                "files": [
                    {
                        "filename": fm.filename,
                        "matchCount": fm.match_count,
                        "context": (
                            [ml.line_content for ml in fm.matching_lines[:context_lines]]
                            if context_lines > 0
                            else []
                        ),
                    }
                    for fm in result.file_matches
                ],
            }
            for result in report.results
        ],
        "summary": {
            "total": report.summary.total_ids,
            "found": report.summary.found_count,
            "notFound": report.summary.not_found_count,
        },
    }
    print(json.dumps(output, indent=2))


def _render_csv(report: SearchReport, context_lines: int) -> None:
    """Render results as flat CSV."""
    writer = csv.writer(sys.stdout)
    writer.writerow(["id", "found", "filename", "matchCount", "context"])

    for result in report.results:
        if result.found:
            for fm in result.file_matches:
                context_str = ""
                if context_lines > 0 and fm.matching_lines:
                    lines_to_show = fm.matching_lines[:context_lines]
                    context_str = " | ".join(
                        ml.line_content for ml in lines_to_show
                    )
                writer.writerow([
                    result.id,
                    "true",
                    fm.filename,
                    fm.match_count,
                    context_str,
                ])
        else:
            writer.writerow([result.id, "false", "", 0, ""])
