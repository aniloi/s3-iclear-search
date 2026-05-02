"""Domain entities for the S3 ICLEAR Fintrans Search Tool."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchRequest:
    """Parsed and validated CLI arguments."""

    date: str
    ids: list[str]
    profile: str
    file_types: list[str]
    bucket: str
    output_format: str = "table"
    context_lines: int = 3
    concurrency: int = 10


@dataclass
class S3FileInfo:
    """Metadata about a single file discovered in S3."""

    key: str
    filename: str
    size: int


@dataclass
class MatchLine:
    """A single matching line within a file."""

    line_number: int
    line_content: str


@dataclass
class FileSearchResult:
    """Result of searching a single file for all IDs."""

    file: S3FileInfo
    matches: dict[str, list[MatchLine]] = field(default_factory=dict)
    error: str | None = None
    retries_used: int = 0


@dataclass
class FileMatch:
    """Matches for a specific ID within a specific file."""

    filename: str
    match_count: int
    matching_lines: list[MatchLine] = field(default_factory=list)


@dataclass
class SearchResult:
    """Aggregated result for a single search ID across all files."""

    id: str
    found: bool
    file_matches: list[FileMatch] = field(default_factory=list)
    total_match_count: int = 0


@dataclass
class SearchSummary:
    """Summary counts for the search report."""

    total_ids: int
    found_count: int
    not_found_count: int


@dataclass
class SearchReport:
    """Final output model containing everything needed to render results."""

    date: str
    bucket: str
    profile: str
    files_searched: int
    files_failed: int
    warnings: list[str]
    results: list[SearchResult]
    summary: SearchSummary
