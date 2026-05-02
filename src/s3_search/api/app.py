"""FastAPI application with all API endpoints and static file serving."""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from s3_search.api.executor import run_search_stream
from s3_search.api.models import (
    ErrorResponse,
    ProfileInfo,
    SavedSearchCreate,
    SavedSearchResponse,
    SearchHistoryEntry,
    SearchSession,
    SearchSessionRequest,
    SearchSessionResponse,
    SearchStatus,
)
from s3_search.api.profiles import detect_profiles
from s3_search.api.session_store import SessionStore
from s3_search.auth import validate_auth
from s3_search.bucket_resolver import resolve_bucket
from s3_search.discovery import VALID_FILE_TYPES
from s3_search.exceptions import AmbiguousProfileError, AuthenticationError

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="S3 Fintrans Search UI",
    description="Web UI for searching AWS S3 ICLEAR files",
    version="1.0.0",
)

# CORS for development (Vite dev server on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared session store (in-memory, per-process)
store = SessionStore()


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/profiles", response_model=list[ProfileInfo])
async def list_profiles() -> list[ProfileInfo]:
    """List available AWS profiles with resolved buckets."""
    return detect_profiles()


@app.get("/api/file-types", response_model=list[str])
async def list_file_types() -> list[str]:
    """List valid file type filter values."""
    return sorted(ft for ft in VALID_FILE_TYPES if ft != "all")


@app.post(
    "/api/search",
    response_model=SearchSessionResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"description": "Validation error"},
    },
)
async def initiate_search(request: SearchSessionRequest) -> SearchSessionResponse:
    """Initiate a new search. Validates credentials synchronously."""
    # Resolve date
    date = request.date
    if date.lower() == "today":
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        request = request.model_copy(update={"date": date})

    # Resolve bucket
    try:
        resolved_bucket = resolve_bucket(request.profile, request.bucket)
    except AmbiguousProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Validate AWS credentials (synchronous)
    try:
        boto3_session = validate_auth(request.profile)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"{exc}. Run: aws sso login --profile {request.profile}",
        )

    # Get caller identity for the auth_ok event
    try:
        sts = boto3_session.client("sts")
        identity = sts.get_caller_identity()
        identity_info = {
            "Account": identity.get("Account", ""),
            "Arn": identity.get("Arn", ""),
        }
    except Exception:
        identity_info = {"Account": "", "Arn": ""}

    # Create session
    session = store.create_session(
        request=request,
        resolved_bucket=resolved_bucket,
        boto3_session=boto3_session,
        identity_info=identity_info,
    )

    return SearchSessionResponse(search_id=session.id)


@app.get("/api/search/{search_id}/stream")
async def stream_search(search_id: str) -> StreamingResponse:
    """SSE endpoint streaming search progress and results."""
    session = store.get_session(search_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Search session not found")

    async def event_generator():
        async for event in run_search_stream(session, store):
            event_type = event.get("event", "message")
            data = event.get("data", "{}")
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/search/{search_id}/results")
async def get_search_results(search_id: str) -> dict[str, Any]:
    """Get final aggregated search results."""
    session = store.get_session(search_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Search session not found")

    if session.status not in (SearchStatus.COMPLETED, SearchStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail=f"Search not yet complete. Status: {session.status.value}",
        )

    if session.report is None:
        raise HTTPException(status_code=404, detail="No results available")

    # Serialize report
    report = session.report
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
                        "context": [
                            ml.line_content
                            for ml in fm.matching_lines[: session.request.context_lines]
                        ]
                        if session.request.context_lines > 0
                        else [],
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


@app.delete("/api/search/{search_id}")
async def cancel_search(search_id: str) -> dict[str, bool]:
    """Cancel an in-progress search."""
    session = store.get_session(search_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Search session not found")

    cancelled = store.cancel_session(search_id)
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail=f"Search is not in progress. Status: {session.status.value}",
        )

    return {"cancelled": True}


@app.get("/api/search/history", response_model=list[SearchHistoryEntry])
async def get_search_history() -> list[SearchHistoryEntry]:
    """Get search history for the current session."""
    return store.get_history()


@app.get("/api/search/{search_id}/export")
async def export_results(
    search_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
) -> StreamingResponse:
    """Export search results as JSON or CSV file download."""
    session = store.get_session(search_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Search session not found")

    if session.status != SearchStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Search not yet complete")

    if session.report is None:
        raise HTTPException(status_code=404, detail="No results available")

    report = session.report
    date = session.request.date
    profile = session.request.profile
    context_lines = session.request.context_lines

    if format == "json":
        content = json.dumps(
            {
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
                                "context": (
                                    [ml.line_content for ml in fm.matching_lines[:context_lines]]
                                    if context_lines > 0
                                    else []
                                ),
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
            },
            indent=2,
        )
        return StreamingResponse(
            iter([content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="search-{date}-{profile}.json"'
            },
        )

    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "found", "filename", "matchCount", "context"])
    for result in report.results:
        if result.found:
            for fm in result.file_matches:
                context_str = ""
                if context_lines > 0 and fm.matching_lines:
                    lines_to_show = fm.matching_lines[:context_lines]
                    context_str = " | ".join(ml.line_content for ml in lines_to_show)
                writer.writerow([result.id, "true", fm.filename, fm.match_count, context_str])
        else:
            writer.writerow([result.id, "false", "", 0, ""])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="search-{date}-{profile}.csv"'
        },
    )


# ---------------------------------------------------------------------------
# Saved Searches
# ---------------------------------------------------------------------------


@app.post("/api/saved-searches", response_model=SavedSearchResponse)
async def create_saved_search(data: SavedSearchCreate) -> SavedSearchResponse:
    """Save a search parameter preset."""
    return store.save_search(data)


@app.get("/api/saved-searches", response_model=list[SavedSearchResponse])
async def list_saved_searches() -> list[SavedSearchResponse]:
    """List all saved search presets."""
    return store.get_saved_searches()


@app.delete("/api/saved-searches/{saved_id}")
async def delete_saved_search(saved_id: str) -> dict[str, bool]:
    """Delete a saved search preset."""
    deleted = store.delete_saved_search(saved_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Static file serving (React build)
# ---------------------------------------------------------------------------

_FRONTEND_DIR = Path(__file__).parent.parent / "static"


def mount_static_files(application: FastAPI, static_dir: Path | None = None) -> None:
    """Mount the React build directory for static file serving.

    Call this after all API routes are registered.
    """
    dist = static_dir or _FRONTEND_DIR
    if not dist.is_dir():
        return

    # Serve static assets (JS, CSS, images)
    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        application.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Catch-all: serve index.html for client-side routing
    index_html = dist / "index.html"
    if index_html.is_file():

        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            # Never intercept API routes
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            # Try to serve the exact file first
            file_path = dist / full_path
            if full_path and file_path.is_file():
                return FileResponse(str(file_path))
            # Fall back to index.html for SPA routing
            return FileResponse(str(index_html))


# Mount static files on import (if build exists)
mount_static_files(app)
