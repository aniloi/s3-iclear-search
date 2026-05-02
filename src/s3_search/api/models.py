"""Pydantic models for the S3 Search API layer."""

from __future__ import annotations

import enum
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator

from s3_search.discovery import VALID_FILE_TYPES
from s3_search.models import SearchReport


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SearchStatus(str, enum.Enum):
    """Lifecycle status of a search session."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# API request / response schemas
# ---------------------------------------------------------------------------

class SearchSessionRequest(BaseModel):
    """JSON body for POST /api/search."""

    date: str = Field(..., min_length=1, description="YYYYMMDD or 'today'")
    ids: list[str] = Field(..., min_length=1, description="Search terms")
    profile: str = Field(..., min_length=1, description="AWS CLI profile name")
    file_types: list[str] = Field(default=["all"], description="File type filters")
    bucket: str | None = Field(default=None, description="Optional bucket override")
    context_lines: int = Field(default=3, ge=0, description="Context lines around matches")

    @field_validator("ids")
    @classmethod
    def ids_must_be_non_empty_strings(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s.strip()]
        if not cleaned:
            raise ValueError("ids must contain at least one non-empty string")
        return cleaned

    @field_validator("file_types")
    @classmethod
    def file_types_must_be_valid(cls, v: list[str]) -> list[str]:
        for ft in v:
            if ft not in VALID_FILE_TYPES:
                valid = ", ".join(sorted(VALID_FILE_TYPES))
                raise ValueError(f"Unknown file type '{ft}'. Valid: {valid}")
        return v

    @field_validator("date")
    @classmethod
    def date_must_be_valid(cls, v: str) -> str:
        if v.lower() == "today":
            return v
        if len(v) != 8 or not v.isdigit():
            raise ValueError("date must be 'today' or YYYYMMDD format")
        try:
            datetime.strptime(v, "%Y%m%d")
        except ValueError:
            raise ValueError(f"'{v}' is not a valid calendar date")
        return v


class SearchSessionResponse(BaseModel):
    """Response for POST /api/search."""

    search_id: str


class ProfileInfo(BaseModel):
    """Information about an available AWS profile."""

    name: str
    resolved_bucket: str | None = None
    is_known: bool = False


class SearchHistoryEntry(BaseModel):
    """Summary of a completed search for the history list."""

    search_id: str
    date: str
    profile: str
    bucket: str
    ids_count: int
    found_count: int
    total_ids: int
    files_searched: int
    status: SearchStatus
    created_at: str
    completed_at: str | None = None


class SavedSearchCreate(BaseModel):
    """Request body for creating a saved search."""

    name: str = Field(..., min_length=1)
    params: SearchSessionRequest


class SavedSearchResponse(BaseModel):
    """A saved search parameter preset."""

    id: str
    name: str
    params: SearchSessionRequest
    created_at: str


class ExportQuery(BaseModel):
    """Query parameters for export endpoint."""

    format: str = Field(default="json", pattern="^(json|csv)$")


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: str = "error"


# ---------------------------------------------------------------------------
# Internal session object (not a Pydantic model — mutable runtime state)
# ---------------------------------------------------------------------------

class SearchSession:
    """In-memory representation of a running or completed search."""

    def __init__(
        self,
        request: SearchSessionRequest,
        resolved_bucket: str,
        boto3_session: Any,
        identity_info: dict[str, str],
    ) -> None:
        self.id: str = uuid.uuid4().hex
        self.status: SearchStatus = SearchStatus.PENDING
        self.request: SearchSessionRequest = request
        self.resolved_bucket: str = resolved_bucket
        self.boto3_session: Any = boto3_session
        self.identity_info: dict[str, str] = identity_info
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.report: SearchReport | None = None
        self.file_results: list[Any] = []
        self.files_total: int = 0
        self.files_completed: int = 0
        self.warnings: list[str] = []
        self.cancelled: threading.Event = threading.Event()

    def to_history_entry(self) -> SearchHistoryEntry:
        """Convert to a history entry summary."""
        found = 0
        total = len(self.request.ids)
        files_searched = 0
        if self.report is not None:
            found = self.report.summary.found_count
            total = self.report.summary.total_ids
            files_searched = self.report.files_searched
        return SearchHistoryEntry(
            search_id=self.id,
            date=self.request.date,
            profile=self.request.profile,
            bucket=self.resolved_bucket,
            ids_count=len(self.request.ids),
            found_count=found,
            total_ids=total,
            files_searched=files_searched,
            status=self.status,
            created_at=self.created_at.isoformat(),
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
        )
