# Code Summary — S3 Fintrans Search UI

## Architecture

```
Browser (React + TypeScript SPA)
    |
    | HTTP REST + SSE
    v
FastAPI Backend (Python)
    |
    | Direct import
    v
Existing s3_search modules (unchanged)
    |
    | boto3
    v
AWS S3
```

## Files Generated

### Backend API Layer (`src/s3_search/api/`)

| File | Description |
|---|---|
| `__init__.py` | Package marker |
| `models.py` | Pydantic models: SearchSessionRequest, SearchSession, SearchStatus, ProfileInfo, SearchHistoryEntry, SavedSearch, SSE event schemas |
| `session_store.py` | Thread-safe in-memory store for sessions, history, and saved searches |
| `profiles.py` | Dynamic AWS profile detection from `~/.aws/config` and `~/.aws/credentials` |
| `executor.py` | Background search executor with asyncio Queue for SSE event production |
| `app.py` | FastAPI application with all endpoints: health, profiles, file-types, search, stream (SSE), results, cancel, history, export, saved searches, static file serving |

### UI Server Entry Point

| File | Description |
|---|---|
| `src/s3_search/ui_server.py` | `s3-search-ui` CLI entry point: starts uvicorn, opens browser |

### Frontend React SPA (`frontend/src/`)

| File | Description |
|---|---|
| `main.tsx` | React entry point |
| `App.tsx` | Root component with global state wiring |
| `index.css` | Tailwind CSS imports + custom styles |
| `types.ts` | All TypeScript interfaces |
| `api.ts` | API client functions (fetch wrappers) |
| `vite-env.d.ts` | Vite type declarations |

### Frontend Hooks (`frontend/src/hooks/`)

| File | Description |
|---|---|
| `useSearch.ts` | Search lifecycle: POST + SSE + incremental results |
| `useProfiles.ts` | Profile fetching |
| `useFileTypes.ts` | File type fetching |
| `useHistory.ts` | Search history |
| `useSavedSearches.ts` | Saved search CRUD |

### Frontend State (`frontend/src/state/`)

| File | Description |
|---|---|
| `AppContext.tsx` | React Context + Provider |
| `reducer.ts` | Global state reducer with all actions |

### Frontend Components (`frontend/src/components/`)

| File | Description |
|---|---|
| `AppLayout.tsx` | Main layout (header + tabs + sidebar + content) |
| `Header.tsx` | App title bar |
| `TabBar.tsx` | Tab switching with status icons and close buttons |
| `Sidebar.tsx` | Sidebar container |
| `SearchForm.tsx` | Search parameter form with validation |
| `ProfileDropdown.tsx` | AWS profile selector with grouped options |
| `FileTypeMultiSelect.tsx` | File type filter multi-select |
| `IdTextarea.tsx` | ID input textarea with live count |
| `SearchProgress.tsx` | Progress steps + bar + cancel button |
| `ResultsView.tsx` | Complete results view (header + warnings + export + table) |
| `ResultsHeader.tsx` | Search metadata display |
| `ResultsTable.tsx` | Interactive sortable/filterable table with expandable rows |
| `WarningsBanner.tsx` | Collapsible warnings |
| `EmptyState.tsx` | Empty state when no tabs |
| `HistoryPanel.tsx` | Search history sidebar |
| `SavedSearches.tsx` | Saved search presets |

### Tests (`tests/`)

| File | Description |
|---|---|
| `test_api_models.py` | Pydantic model validation + SessionStore tests |
| `test_api_profiles.py` | Profile detection with mocked AWS config |
| `test_api_executor.py` | Background search executor with mocked S3 |
| `test_api_app.py` | FastAPI endpoint tests using TestClient |

### Configuration

| File | Description |
|---|---|
| `pyproject.toml` | Updated: v2.0.0, new deps (fastapi, uvicorn, sse-starlette, pydantic), new entry point (s3-search-ui), package data for static files |
| `Makefile` | Build targets: install, build-frontend, dev, test |
| `frontend/package.json` | React + TypeScript + Vite + Tailwind dependencies |
| `frontend/tsconfig.json` | TypeScript configuration |
| `frontend/vite.config.ts` | Vite config with API proxy and build output to src/s3_search/static |
| `frontend/tailwind.config.js` | Tailwind CSS configuration |
| `frontend/postcss.config.js` | PostCSS configuration |
| `frontend/index.html` | HTML entry point |

## Build Instructions

### Development (two terminals)

```bash
# Terminal 1: Backend
pip install -e ".[dev]"
uvicorn s3_search.api.app:app --reload --port 8080

# Terminal 2: Frontend (with API proxy)
cd frontend && npm install && npm run dev
```

### Production Build

```bash
# Build frontend + install package
make install

# Or step by step:
cd frontend && npm install && npm run build  # builds to src/s3_search/static/
cd .. && pip install -e ".[ui]"

# Run
s3-search-ui --port 8080
```

### Running Tests

```bash
pip install -e ".[dev]"
pytest -v
```

## Key Design Decisions

1. **SSE over WebSockets**: Simpler, unidirectional server-to-client streaming is sufficient
2. **In-memory state**: No database — session-only persistence as specified
3. **Bundled static files**: React build output goes into `src/s3_search/static/`, served by FastAPI
4. **Direct module import**: API layer imports existing `s3_search` modules directly (no subprocess)
5. **Thread-based parallelism**: Reuses existing ThreadPoolExecutor pattern from CLI search engine
6. **Sync auth in POST**: Fail fast on credential errors before creating SSE connection
