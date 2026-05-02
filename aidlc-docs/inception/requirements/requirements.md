# S3 ICLEAR Fintrans Search Tool — Front-End / UI Requirements

## Intent Analysis

- **User Request**: Build a web-based front-end / UI for the existing S3 Fintrans Search CLI tool
- **Request Type**: Enhancement — adding a React + TypeScript SPA with a FastAPI backend to an existing Python CLI tool
- **Scope**: Multiple Components — React front-end, FastAPI API layer, integration with existing search modules, bundled packaging
- **Complexity**: Moderate-to-High — SPA with streaming results (SSE), multi-tab support, session state, and bundled distribution within an existing pip package

---

## 1. Functional Requirements

### FR-1: FastAPI Backend API

The system shall expose a REST API (FastAPI) that wraps the existing `s3_search` modules:

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/health` | GET | Health check — returns `{"status": "ok"}` |
| `GET /api/profiles` | GET | Returns the list of known profile-to-bucket mappings |
| `GET /api/file-types` | GET | Returns the list of valid file type filter values |
| `POST /api/search` | POST | Initiates a search. Accepts JSON body with search parameters. Returns a `search_id` for tracking. |
| `GET /api/search/{search_id}/stream` | GET | SSE (Server-Sent Events) endpoint. Streams search progress and results in real time. |
| `GET /api/search/{search_id}/results` | GET | Returns the final aggregated search results (once complete). |
| `GET /api/search/history` | GET | Returns the list of searches performed in the current session. |
| `POST /api/search/{search_id}/export` | POST | Exports results in the specified format (`json`, `csv`). Returns the file content. |

#### FR-1.1: Search Request Body

```json
{
  "date": "20260501",
  "ids": ["PAY-123", "ACC-456"],
  "profile": "qa",
  "file_types": ["fintrans", "ordertrans"],
  "bucket": null,
  "context_lines": 3
}
```

- `date`: Required. `YYYYMMDD` or `"today"`.
- `ids`: Required. Array of search term strings.
- `profile`: Required. AWS CLI profile name.
- `file_types`: Optional. Array of file type filters. Default: `["all"]`.
- `bucket`: Optional. Override bucket. Default: `null` (auto-resolve from profile).
- `context_lines`: Optional. Default: `3`.

#### FR-1.2: SSE Stream Events

The `/api/search/{search_id}/stream` endpoint shall emit the following event types:

| Event Type | Payload | Description |
|---|---|---|
| `auth_ok` | `{"profile": "qa", "account": "..."}` | AWS authentication succeeded |
| `discovery` | `{"files_found": 134, "files": [...]}` | File discovery complete |
| `file_start` | `{"filename": "...", "index": 1, "total": 134}` | Starting to search a file |
| `file_complete` | `{"filename": "...", "matches": {...}, "error": null}` | File search complete with per-ID matches |
| `search_complete` | `{"report": {...}}` | Full aggregated report (same structure as CLI JSON output) |
| `error` | `{"message": "...", "code": "..."}` | Fatal error (auth failure, path not found, etc.) |

#### FR-1.3: Authentication Validation

The API shall validate AWS credentials using the same logic as the CLI (`auth.py`):
1. Create a boto3 session with the specified profile.
2. Call STS `get_caller_identity()`.
3. If authentication fails, return an `error` SSE event with the profile name and a hint to run `aws sso login --profile {profile}`.

#### FR-1.4: Bucket Resolution

The API shall use the existing `bucket_resolver.py` logic to auto-resolve the bucket from the profile name. The `--bucket` override is supported via the `bucket` field in the request body.

### FR-2: React Front-End — Search Form

The UI shall provide a search form with the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| Date | Text input | Yes | Accepts `YYYYMMDD` or `today`. Date picker optional enhancement. |
| Search IDs | Textarea | Yes | One ID per line, or comma-separated. |
| AWS Profile | Dropdown | Yes | Populated from `/api/profiles`. Shows profile name and auto-resolved bucket. |
| File Type Filter | Multi-select | No | Populated from `/api/file-types`. Default: All. |
| Bucket Override | Text input | No | Overrides the auto-resolved bucket. Hidden by default, shown via "Advanced" toggle. |
| Context Lines | Number input | No | Default: `3`. Range: `0–20`. |

The form shall have a **Search** button that submits the request and opens a new results tab.

### FR-3: React Front-End — Results Display

#### FR-3.1: Interactive Results Table

The results table shall display:

| Column | Description |
|---|---|
| ID | The search term |
| Status | Found (green checkmark) / Not Found (red cross) |
| Files | Comma-separated list of matching filenames |
| Match Count | Total number of matching lines across all files |

The table shall support:
- **Sorting** by any column (click column header)
- **Filtering** by status (All / Found / Not Found)
- **Text search** across IDs
- **Expandable rows**: clicking a row expands it to show matching CSV lines (context) grouped by file

#### FR-3.2: Search Metadata Header

Above the results table, display:
- Date searched
- Bucket name
- Profile used
- Files searched count
- Files failed count (if any, with warning styling)

#### FR-3.3: Warnings Display

If any files failed (access denied, retries exhausted), display warnings in a collapsible warning banner above the results table.

### FR-4: React Front-End — Real-Time Progress

During a search, the UI shall:
1. Show an **authentication** step indicator (checking credentials).
2. Show a **discovery** step indicator (listing files).
3. Show a **progress bar** with `{completed}/{total}` files and percentage.
4. Stream individual file results into the results table as they complete.
5. Transition to the final results view when `search_complete` is received.

### FR-5: React Front-End — Multi-Tab Support

The UI shall support multiple concurrent searches in tabs:
- Each search opens in a new tab.
- Tabs show: search date + profile (e.g., "20260501 / qa").
- Users can switch between tabs to view different search results.
- Closing a tab removes it from the session.
- A "+" button or "New Search" action opens a fresh search form tab.

### FR-6: React Front-End — Search History

The UI shall maintain an in-memory search history for the current session:
- Each completed search is added to the history list.
- History shows: timestamp, date searched, profile, IDs count, found/total summary.
- Clicking a history entry re-opens its results in a new tab (read-only, no re-execution).
- History is accessible via a sidebar or dropdown.
- History is lost when the browser tab is closed or the server is restarted.

### FR-7: React Front-End — Saved Searches (Session-Only)

The UI shall allow users to save search parameter presets during the session:
- A "Save Search" button on the search form saves the current parameters (date, IDs, profile, file types, etc.) with a user-provided name.
- Saved searches appear in a list and can be loaded into the search form with one click.
- Saved searches are in-memory only — lost when the session ends.

### FR-8: React Front-End — Export

The UI shall support exporting search results:
- **Export JSON**: Downloads the full search report as a `.json` file.
- **Export CSV**: Downloads the flat CSV format (same as CLI `--output csv`).
- Export buttons are available on the results view for each tab.

### FR-9: Static File Serving

The FastAPI backend shall serve the React build artifacts (HTML, JS, CSS) as static files:
- The React app is served at the root URL (`/`).
- API endpoints are under `/api/`.
- This enables single-process deployment — one command starts both the API and the UI.

### FR-10: CLI Integration

The UI shall be launchable from the existing CLI:
- Command: `s3-search-ui` (new console entry point).
- Starts the FastAPI server on `localhost:8080` (configurable via `--port`).
- Automatically opens the default browser to the UI URL.
- Prints the URL to the terminal: `S3 Search UI running at http://localhost:8080`.
- `Ctrl+C` gracefully shuts down the server.

---

## 2. Non-Functional Requirements

### NFR-1: Technology Stack

- **Backend**: Python 3.9+, FastAPI, uvicorn, `sse-starlette` (for SSE support)
- **Frontend**: React 18+, TypeScript, Vite (build tool)
- **Styling**: Tailwind CSS or a lightweight component library (e.g., shadcn/ui)
- **State Management**: React built-in state (useState/useReducer) + Context API
- **HTTP Client**: fetch API with EventSource for SSE
- **Existing Dependencies**: `boto3` (already present), `s3_search` modules (direct import)

### NFR-2: Performance

- The API shall handle concurrent search requests (multiple tabs) without blocking.
- SSE streaming shall deliver file-level results within 1 second of each file completing.
- The React UI shall render incrementally — no full-page re-renders on each SSE event.
- The bundled React build shall be optimized (minified, tree-shaken) for fast initial load.

### NFR-3: Packaging

- The React build output (`dist/`) shall be included in the Python package as package data.
- FastAPI serves these static files at runtime — no separate Node.js server needed.
- The `pyproject.toml` shall be updated to:
  - Add `fastapi`, `uvicorn[standard]`, and `sse-starlette` as dependencies.
  - Add an `s3-search-ui` console entry point.
  - Include the React build artifacts in package data.
- A build script or Makefile target shall build the React app and copy artifacts into the Python package before `pip install`.

### NFR-4: Deployment Flexibility

- **Local**: `s3-search-ui` runs on localhost, single user.
- **Shared**: Can be deployed behind a reverse proxy (nginx, etc.) for team access. The app shall not assume localhost — use relative URLs for API calls.
- **No authentication layer**: The UI relies on the user's local AWS credentials. No additional auth is added (same security model as the CLI).

### NFR-5: Browser Compatibility

- Support modern evergreen browsers: Chrome, Firefox, Safari, Edge (latest 2 versions).
- No IE11 support required.

### NFR-6: Accessibility

- The UI shall follow basic WCAG 2.1 Level A guidelines:
  - Semantic HTML elements
  - Keyboard navigable (tab order, focus management)
  - ARIA labels on interactive elements
  - Sufficient color contrast
  - Screen reader compatible table structure

### NFR-7: Error Handling

- **API errors**: Return structured JSON error responses with HTTP status codes.
- **SSE connection loss**: The UI shall detect disconnection and show a reconnect option.
- **Invalid form input**: Client-side validation with clear error messages before submission.
- **Backend exceptions**: Caught and returned as structured error events — no unhandled 500s.

---

## 3. Architecture Overview

```
+--------------------------------------------------+
|                   Browser                        |
|  +--------------------------------------------+  |
|  |         React + TypeScript SPA             |  |
|  |  - Search Form                             |  |
|  |  - Results Table (interactive)             |  |
|  |  - Multi-Tab Layout                        |  |
|  |  - Search History Sidebar                  |  |
|  |  - SSE Client (EventSource)                |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
          |  HTTP REST + SSE  |
          v                   v
+--------------------------------------------------+
|              FastAPI Backend                      |
|  +--------------------------------------------+  |
|  |  /api/search (POST)                        |  |
|  |  /api/search/{id}/stream (GET, SSE)        |  |
|  |  /api/search/{id}/results (GET)            |  |
|  |  /api/profiles (GET)                       |  |
|  |  /api/file-types (GET)                     |  |
|  |  /api/search/history (GET)                 |  |
|  |  Static file serving (React build)         |  |
|  +--------------------------------------------+  |
|  |  Direct import: s3_search modules          |  |
|  |  - auth.py, bucket_resolver.py             |  |
|  |  - discovery.py, search.py, models.py      |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
          |
          v
+--------------------------------------------------+
|              AWS S3 (via boto3)                   |
+--------------------------------------------------+
```

---

## 4. API-to-CLI Mapping

| CLI Parameter | API Field | Notes |
|---|---|---|
| `--date` | `date` | Same validation (YYYYMMDD or "today") |
| `--id` / `--id-file` | `ids` (array) | UI handles both inline and file upload |
| `--profile` | `profile` | Dropdown populated from known profiles |
| `--file-type` | `file_types` (array) | Multi-select in UI |
| `--bucket` | `bucket` | Optional override, hidden in "Advanced" |
| `--output` | N/A | UI always uses structured data; export handles format |
| `--context` | `context_lines` | Number input, default 3 |

---

## 5. Out of Scope (V1 UI)

- User authentication/authorization layer (relies on local AWS credentials)
- Persistent database (all state is session-only)
- File upload for `--id-file` (user pastes IDs into textarea instead)
- Dark mode / theme switching
- Internationalization (i18n)
- Mobile-responsive layout (desktop-first)
- WebSocket transport (SSE is sufficient for server-to-client streaming)
