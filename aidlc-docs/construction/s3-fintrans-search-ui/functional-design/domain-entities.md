# Domain Entities — S3 Fintrans Search UI

## Entity Relationship Overview

```
Browser (React SPA)
  |
  +-> POST /api/search  ──> SearchSession created (UUID)
  |     |
  |     +-> validates auth (sync)
  |     +-> returns search_id
  |
  +-> GET /api/search/{id}/stream  ──> SSE EventStream
  |     |
  |     +-> discovery event
  |     +-> file_start / file_complete events (per file)
  |     +-> search_complete event (final report)
  |
  +-> GET /api/search/{id}/results  ──> SearchReport (JSON)
  +-> DELETE /api/search/{id}       ──> Cancel search
  +-> GET /api/search/history       ──> list[SearchHistoryEntry]
  +-> GET /api/profiles             ──> list[ProfileInfo]
  +-> GET /api/file-types           ──> list[str]
```

---

## Backend Entities (Python / FastAPI)

### 1. SearchSessionRequest

API request body for `POST /api/search`.

```
SearchSessionRequest:
    date: str                    # YYYYMMDD or 'today'
    ids: list[str]               # Search terms
    profile: str                 # AWS CLI profile name
    file_types: list[str]        # File type filters, default ['all']
    bucket: str | None           # Optional bucket override
    context_lines: int           # Default: 3
```

**Validation**: Same rules as CLI — date format, non-empty IDs, valid file types. Returns HTTP 422 on validation failure.

### 2. SearchSession

In-memory representation of a running or completed search.

```
SearchSession:
    id: str                      # UUID4 string
    status: SearchStatus         # PENDING | RUNNING | COMPLETED | CANCELLED | FAILED
    request: SearchSessionRequest
    resolved_bucket: str         # Bucket after profile resolution
    boto3_session: Session       # Authenticated boto3 session
    created_at: datetime         # UTC timestamp
    completed_at: datetime | None
    report: SearchReport | None  # Final aggregated report (when complete)
    file_results: list[FileSearchResult]  # Accumulated per-file results
    files_total: int             # Total files to search
    files_completed: int         # Files searched so far
    warnings: list[str]          # Accumulated warnings
    cancelled: threading.Event   # Cancellation signal
```

### 3. SearchStatus (Enum)

```
SearchStatus:
    PENDING     # Created, auth validated, not yet streaming
    RUNNING     # File discovery and/or search in progress
    COMPLETED   # All files searched, report generated
    CANCELLED   # User cancelled via DELETE
    FAILED      # Fatal error (auth, path not found, etc.)
```

### 4. SSEEvent

Represents a single Server-Sent Event to be pushed to the client.

```
SSEEvent:
    event: str                   # Event type name
    data: dict                   # JSON-serializable payload
```

Event types and payloads:

| Event Type | Payload |
|---|---|
| `auth_ok` | `{"profile": str, "account": str, "arn": str}` |
| `discovery` | `{"files_found": int, "files": [{"filename": str, "size": int}]}` |
| `file_start` | `{"filename": str, "index": int, "total": int}` |
| `file_complete` | `{"filename": str, "matches": {id: [{"line_number": int, "line_content": str}]}, "error": str\|null}` |
| `search_complete` | `{"report": SearchReport (JSON dict)}` |
| `cancelled` | `{"message": "Search cancelled by user"}` |
| `error` | `{"message": str, "code": str}` |

### 5. ProfileInfo

Information about an available AWS profile.

```
ProfileInfo:
    name: str                    # Profile name from ~/.aws/config
    resolved_bucket: str | None  # Auto-resolved bucket (null if no match)
    is_known: bool               # True if profile matches a known environment
```

### 6. SearchHistoryEntry

Summary of a completed search for the history list.

```
SearchHistoryEntry:
    search_id: str               # UUID
    date: str                    # Search date
    profile: str                 # AWS profile used
    bucket: str                  # Bucket searched
    ids_count: int               # Number of IDs searched
    found_count: int             # IDs found
    total_ids: int               # Total IDs
    files_searched: int          # Files searched
    status: SearchStatus         # Final status
    created_at: str              # ISO timestamp
    completed_at: str | None     # ISO timestamp
```

### 7. SavedSearch

A saved search parameter preset (session-only, in-memory).

```
SavedSearch:
    id: str                      # UUID
    name: str                    # User-provided name
    params: SearchSessionRequest # Saved form parameters
    created_at: str              # ISO timestamp
```

### 8. SessionStore

In-memory store for all search sessions (per server process).

```
SessionStore:
    _sessions: dict[str, SearchSession]    # search_id -> session
    _history: list[SearchHistoryEntry]     # Ordered by created_at desc
    _saved_searches: list[SavedSearch]     # User-saved presets

    create_session(request, boto3_session, resolved_bucket) -> SearchSession
    get_session(search_id) -> SearchSession | None
    cancel_session(search_id) -> bool
    add_to_history(session) -> None
    get_history() -> list[SearchHistoryEntry]
    save_search(name, params) -> SavedSearch
    get_saved_searches() -> list[SavedSearch]
    delete_saved_search(id) -> bool
```

---

## Frontend Entities (TypeScript / React)

### 9. SearchFormData

Form state for the search form component.

```typescript
SearchFormData:
    date: string                 // YYYYMMDD or 'today'
    ids: string                  // Raw textarea content (newline or comma separated)
    profile: string              // Selected profile name
    fileTypes: string[]          // Selected file type filters
    bucket: string               // Optional bucket override (empty = auto)
    contextLines: number         // Default: 3
```

### 10. SearchTab

State for a single results tab.

```typescript
SearchTab:
    id: string                   // UUID (matches backend search_id)
    label: string                // Display label: "YYYYMMDD / profile"
    status: 'connecting' | 'authenticating' | 'discovering' | 'searching' | 'complete' | 'cancelled' | 'error'
    params: SearchFormData       // The parameters used for this search
    authInfo: AuthInfo | null    // From auth_ok event
    discovery: DiscoveryInfo | null  // From discovery event
    fileProgress: FileProgress   // Tracking per-file progress
    results: SearchResult[]      // Accumulated per-ID results (built incrementally)
    report: SearchReport | null  // Final report from search_complete
    warnings: string[]           // Accumulated warnings
    error: string | null         // Error message if failed
```

### 11. FileProgress

Tracks file-level search progress for the progress bar.

```typescript
FileProgress:
    total: number                // Total files to search
    completed: number            // Files completed so far
    currentFile: string | null   // Currently searching filename
    percentage: number           // Computed: (completed / total) * 100
```

### 12. AuthInfo

```typescript
AuthInfo:
    profile: string
    account: string
    arn: string
```

### 13. DiscoveryInfo

```typescript
DiscoveryInfo:
    filesFound: number
    files: { filename: string, size: number }[]
```

### 14. ProfileOption

For the profile dropdown.

```typescript
ProfileOption:
    name: string                 // Profile name
    resolvedBucket: string | null
    isKnown: boolean             // Matches a known environment
```

---

## Reused Entities (from existing CLI)

The following entities from `src/s3_search/models.py` are reused as-is by the API layer:

- **SearchRequest** — constructed from SearchSessionRequest + resolved bucket
- **S3FileInfo** — file metadata from discovery
- **FileSearchResult** — per-file search results
- **MatchLine** — individual matching line
- **FileMatch** — matches for one ID in one file
- **SearchResult** — aggregated per-ID results
- **SearchSummary** — found/not-found counts
- **SearchReport** — final output model

The API serializes these to JSON for the SSE stream and REST responses.
