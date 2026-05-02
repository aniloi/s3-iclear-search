"""Background search executor with SSE event production."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from s3_search.api.models import SearchSession, SearchStatus
from s3_search.api.session_store import SessionStore
from s3_search.discovery import discover_files
from s3_search.exceptions import S3PathNotFoundError
from s3_search.models import SearchRequest
from s3_search.search import _search_single_file, aggregate_results

logger = logging.getLogger(__name__)


def _match_line_to_dict(ml: Any) -> dict[str, Any]:
    return {"line_number": ml.line_number, "line_content": ml.line_content}


def _file_result_matches_to_dict(matches: dict[str, list[Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        search_id: [_match_line_to_dict(ml) for ml in lines]
        for search_id, lines in matches.items()
    }


def _report_to_dict(report: Any) -> dict[str, Any]:
    """Convert a SearchReport to a JSON-serializable dict."""
    return {
        "date": report.date,
        "bucket": report.bucket,
        "profile": report.profile,
        "filesSearched": report.files_searched,
        "filesFailed": report.files_failed,
        "warnings": report.warnings,
        "results": [
            {
                "id": r.id,
                "found": r.found,
                "totalMatchCount": r.total_match_count,
                "files": [
                    {
                        "filename": fm.filename,
                        "matchCount": fm.match_count,
                        "context": [ml.line_content for ml in fm.matching_lines],
                    }
                    for fm in r.file_matches
                ],
            }
            for r in report.results
        ],
        "summary": {
            "total": report.summary.total_ids,
            "found": report.summary.found_count,
            "notFound": report.summary.not_found_count,
        },
    }


async def run_search_stream(
    session: SearchSession,
    store: SessionStore,
) -> AsyncGenerator[dict[str, str], None]:
    """Execute a search and yield SSE events as dicts with 'event' and 'data' keys.

    This is an async generator consumed by the SSE endpoint.
    Events are produced by a background thread via an asyncio Queue.
    """
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[dict[str, str] | None] = asyncio.Queue()

    def _run_in_thread() -> None:
        """Blocking search logic that pushes events onto the async queue."""
        try:
            # --- Auth OK (already validated in POST handler) ---
            _put(queue, loop, "auth_ok", {
                "profile": session.request.profile,
                "account": session.identity_info.get("Account", ""),
                "arn": session.identity_info.get("Arn", ""),
            })

            session.status = SearchStatus.RUNNING

            # --- File Discovery ---
            try:
                file_types = session.request.file_types
                if file_types == ["all"]:
                    file_types = ["all"]
                files = discover_files(
                    session.boto3_session,
                    session.resolved_bucket,
                    session.request.date,
                    file_types,
                )
            except S3PathNotFoundError as exc:
                _put(queue, loop, "error", {
                    "message": str(exc),
                    "code": "s3_path_not_found",
                })
                session.status = SearchStatus.FAILED
                session.completed_at = datetime.now(timezone.utc)
                store.add_to_history(session)
                _put_sentinel(queue, loop)
                return

            if not files:
                _put(queue, loop, "error", {
                    "message": f"No files matching type filter found for date {session.request.date}",
                    "code": "no_files",
                })
                session.status = SearchStatus.FAILED
                session.completed_at = datetime.now(timezone.utc)
                store.add_to_history(session)
                _put_sentinel(queue, loop)
                return

            session.files_total = len(files)
            _put(queue, loop, "discovery", {
                "files_found": len(files),
                "files": [{"filename": f.filename, "size": f.size} for f in files],
            })

            # --- Parallel Search ---
            completed_results = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(
                        _search_single_file,
                        session.boto3_session,
                        session.resolved_bucket,
                        session.request.ids,
                        f,
                    ): (i, f)
                    for i, f in enumerate(files)
                }

                for future in as_completed(futures):
                    if session.cancelled.is_set():
                        # Cancel remaining futures
                        for f in futures:
                            f.cancel()
                        break

                    idx, file_info = futures[future]
                    _put(queue, loop, "file_start", {
                        "filename": file_info.filename,
                        "index": session.files_completed + 1,
                        "total": session.files_total,
                    })

                    result = future.result()
                    session.files_completed += 1
                    session.file_results.append(result)
                    completed_results.append(result)

                    _put(queue, loop, "file_complete", {
                        "filename": file_info.filename,
                        "matches": _file_result_matches_to_dict(result.matches),
                        "error": result.error,
                    })

            # --- Check cancellation ---
            if session.cancelled.is_set():
                # Build partial report
                request = SearchRequest(
                    date=session.request.date,
                    ids=session.request.ids,
                    profile=session.request.profile,
                    file_types=session.request.file_types,
                    bucket=session.resolved_bucket,
                    context_lines=session.request.context_lines,
                )
                session.report = aggregate_results(request, completed_results)
                session.completed_at = datetime.now(timezone.utc)
                store.add_to_history(session)
                _put(queue, loop, "cancelled", {"message": "Search cancelled by user"})
                _put_sentinel(queue, loop)
                return

            # --- Aggregate and Complete ---
            request = SearchRequest(
                date=session.request.date,
                ids=session.request.ids,
                profile=session.request.profile,
                file_types=session.request.file_types,
                bucket=session.resolved_bucket,
                context_lines=session.request.context_lines,
            )
            report = aggregate_results(request, completed_results)
            session.report = report
            session.status = SearchStatus.COMPLETED
            session.completed_at = datetime.now(timezone.utc)
            store.add_to_history(session)

            _put(queue, loop, "search_complete", {"report": _report_to_dict(report)})

        except Exception as exc:
            logger.exception("Search executor error")
            _put(queue, loop, "error", {
                "message": str(exc),
                "code": "internal_error",
            })
            session.status = SearchStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            store.add_to_history(session)
        finally:
            _put_sentinel(queue, loop)

    # Start the blocking search in a thread
    loop.run_in_executor(None, _run_in_thread)

    # Yield SSE events from the queue
    while True:
        event = await queue.get()
        if event is None:
            break
        yield event


def _put(
    queue: asyncio.Queue[dict[str, str] | None],
    loop: asyncio.AbstractEventLoop,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Thread-safe put of an SSE event dict onto the async queue."""
    msg = {"event": event_type, "data": json.dumps(data)}
    asyncio.run_coroutine_threadsafe(queue.put(msg), loop)


def _put_sentinel(
    queue: asyncio.Queue[dict[str, str] | None],
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Thread-safe put of the sentinel (None) to signal stream end."""
    asyncio.run_coroutine_threadsafe(queue.put(None), loop)
