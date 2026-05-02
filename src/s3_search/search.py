"""Parallel S3 file search engine."""

from __future__ import annotations

import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.exceptions import ClientError

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

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


def search_files(
    session: boto3.Session,
    request: SearchRequest,
    files: list[S3FileInfo],
) -> list[FileSearchResult]:
    """Search multiple S3 files in parallel for the given IDs.

    Args:
        session: Authenticated boto3 session.
        request: The search request with IDs and configuration.
        files: List of S3 files to search.

    Returns:
        List of FileSearchResult, one per file.
    """
    results: list[FileSearchResult] = []

    with ThreadPoolExecutor(max_workers=request.concurrency) as executor:
        futures = {
            executor.submit(
                _search_single_file, session, request.bucket, request.ids, file_info
            ): file_info
            for file_info in files
        }
        for future in as_completed(futures):
            results.append(future.result())

    return results


def _search_single_file(
    session: boto3.Session,
    bucket: str,
    ids: list[str],
    file_info: S3FileInfo,
) -> FileSearchResult:
    """Search a single S3 file for all IDs with retry logic.

    Streams the file line-by-line and checks each line for literal
    substring matches against all search IDs.

    Access denied errors are not retried. Other errors are retried
    up to MAX_RETRIES times with exponential backoff.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            s3 = session.client("s3")
            response = s3.get_object(Bucket=bucket, Key=file_info.key)
            body = response["Body"]

            matches: dict[str, list[MatchLine]] = {}
            line_number = 0

            # Wrap the streaming body for line-by-line reading
            text_stream = io.TextIOWrapper(body, encoding="utf-8", errors="replace")
            try:
                for line in text_stream:
                    line_number += 1
                    line = line.rstrip("\n").rstrip("\r")
                    for search_id in ids:
                        if search_id in line:
                            if search_id not in matches:
                                matches[search_id] = []
                            matches[search_id].append(
                                MatchLine(
                                    line_number=line_number,
                                    line_content=line,
                                )
                            )
            finally:
                body.close()

            return FileSearchResult(
                file=file_info,
                matches=matches,
                error=None,
                retries_used=attempt - 1,
            )

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "403"):
                # Access denied — do not retry
                return FileSearchResult(
                    file=file_info,
                    matches={},
                    error=f"Access denied: {file_info.filename}",
                    retries_used=attempt - 1,
                )
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE**attempt)
                continue
            return FileSearchResult(
                file=file_info,
                matches={},
                error=f"Failed after {MAX_RETRIES} retries: {file_info.filename}: {exc}",
                retries_used=attempt - 1,
            )

        except Exception as exc:
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE**attempt)
                continue
            return FileSearchResult(
                file=file_info,
                matches={},
                error=f"Failed after {MAX_RETRIES} retries: {file_info.filename}: {exc}",
                retries_used=attempt - 1,
            )

    # Should not reach here, but satisfy type checker
    return FileSearchResult(
        file=file_info,
        matches={},
        error=f"Unexpected failure: {file_info.filename}",
        retries_used=MAX_RETRIES,
    )


def aggregate_results(
    request: SearchRequest,
    file_results: list[FileSearchResult],
) -> SearchReport:
    """Aggregate per-file search results into a unified report.

    Args:
        request: The original search request.
        file_results: Results from searching each file.

    Returns:
        A SearchReport with per-ID aggregated results and summary.
    """
    warnings: list[str] = []
    files_failed = 0

    for fr in file_results:
        if fr.error is not None:
            warnings.append(fr.error)
            files_failed += 1

    results: list[SearchResult] = []
    for search_id in request.ids:
        file_matches: list[FileMatch] = []
        total_count = 0
        for fr in file_results:
            if search_id in fr.matches:
                lines = fr.matches[search_id]
                file_matches.append(
                    FileMatch(
                        filename=fr.file.filename,
                        match_count=len(lines),
                        matching_lines=lines,
                    )
                )
                total_count += len(lines)
        results.append(
            SearchResult(
                id=search_id,
                found=len(file_matches) > 0,
                file_matches=file_matches,
                total_match_count=total_count,
            )
        )

    found_count = sum(1 for r in results if r.found)
    summary = SearchSummary(
        total_ids=len(request.ids),
        found_count=found_count,
        not_found_count=len(request.ids) - found_count,
    )

    return SearchReport(
        date=request.date,
        bucket=request.bucket,
        profile=request.profile,
        files_searched=len(file_results) - files_failed,
        files_failed=files_failed,
        warnings=warnings,
        results=results,
        summary=summary,
    )
