"""CLI entry point for the S3 ICLEAR Fintrans Search Tool."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from s3_search.auth import validate_auth
from s3_search.bucket_resolver import resolve_bucket
from s3_search.discovery import VALID_FILE_TYPES, discover_files
from s3_search.exceptions import (
    AmbiguousProfileError,
    AuthenticationError,
    S3PathNotFoundError,
)
from s3_search.models import SearchRequest
from s3_search.renderers import render_report
from s3_search.search import aggregate_results, search_files


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="s3-search",
        description="Search AWS S3 ICLEAR_S3 files for payment/account/order identifiers.",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Date folder to search (YYYYMMDD or 'today' for current UTC date).",
    )

    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument(
        "--id",
        help="Comma-separated search terms.",
    )
    id_group.add_argument(
        "--id-file",
        help="Path to file with one search term per line.",
    )

    parser.add_argument(
        "--profile",
        required=True,
        help="AWS CLI profile name (e.g., qa, uat, prod).",
    )
    parser.add_argument(
        "--file-type",
        default="all",
        help=(
            "Filter file types to search. Options: "
            + ", ".join(sorted(VALID_FILE_TYPES))
            + ". Comma-separated for multiple. Default: all."
        ),
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Override S3 bucket (default: environment-aware based on profile).",
    )
    parser.add_argument(
        "--output",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format. Default: table.",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=3,
        help="Number of context lines around matches. Default: 3. Set to 0 to suppress.",
    )
    return parser


def _resolve_date(date_str: str) -> str:
    """Resolve the date string, handling 'today' as current UTC date."""
    if date_str.lower() == "today":
        return datetime.now(timezone.utc).strftime("%Y%m%d")

    # Validate YYYYMMDD format
    if len(date_str) != 8 or not date_str.isdigit():
        print(
            f"Error: Invalid date format '{date_str}'. Expected YYYYMMDD or 'today'.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Validate it's a real date
    try:
        datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        print(
            f"Error: Invalid date '{date_str}'. Not a valid calendar date.",
            file=sys.stderr,
        )
        sys.exit(2)

    return date_str


def _resolve_ids_from_file(filepath: str) -> list[str]:
    """Parse IDs from a file, skipping blank lines and comments."""
    if not os.path.isfile(filepath):
        print(f"Error: ID file not found: {filepath}", file=sys.stderr)
        sys.exit(2)

    ids: list[str] = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            ids.append(stripped)

    if not ids:
        print(f"Error: No IDs found in file: {filepath}", file=sys.stderr)
        sys.exit(2)

    return ids


def _resolve_ids(id_arg: str | None, id_file_arg: str | None) -> list[str]:
    """Resolve the list of search IDs from --id or --id-file."""
    if id_arg is not None:
        ids = [s.strip() for s in id_arg.split(",") if s.strip()]
        if not ids:
            print("Error: --id value is empty.", file=sys.stderr)
            sys.exit(2)
        return ids

    if id_file_arg is not None:
        return _resolve_ids_from_file(id_file_arg)

    # Should not reach here due to argparse mutual exclusivity
    print("Error: One of --id or --id-file is required.", file=sys.stderr)
    sys.exit(2)


def _validate_file_types(file_type_arg: str) -> list[str]:
    """Validate and parse the --file-type argument."""
    types = [t.strip().lower() for t in file_type_arg.split(",") if t.strip()]

    for ft in types:
        if ft not in VALID_FILE_TYPES:
            valid_str = ", ".join(sorted(VALID_FILE_TYPES))
            print(
                f"Error: Unknown file type '{ft}'. Valid options: {valid_str}",
                file=sys.stderr,
            )
            sys.exit(2)

    if "all" in types:
        return ["all"]

    return types


def main() -> None:
    """Main entry point for the s3-search CLI tool."""
    parser = _build_parser()
    args = parser.parse_args()

    # Step 1: Parse and validate arguments
    date = _resolve_date(args.date)
    ids = _resolve_ids(args.id, args.id_file)
    file_types = _validate_file_types(args.file_type)

    try:
        bucket = resolve_bucket(args.profile, args.bucket)
    except AmbiguousProfileError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    request = SearchRequest(
        date=date,
        ids=ids,
        profile=args.profile,
        file_types=file_types,
        bucket=bucket,
        output_format=args.output,
        context_lines=args.context,
    )

    # Step 2: Validate AWS authentication
    try:
        session = validate_auth(request.profile)
    except AuthenticationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Discover files
    try:
        files = discover_files(session, request.bucket, request.date, request.file_types)
    except S3PathNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not files:
        # No files matched the filter — warning already printed, exit 0
        sys.exit(0)

    # Step 4: Search files in parallel
    file_results = search_files(session, request, files)

    # Step 5: Aggregate results
    report = aggregate_results(request, file_results)

    # Step 6: Render output
    render_report(report, request.output_format, request.context_lines)

    sys.exit(0)
