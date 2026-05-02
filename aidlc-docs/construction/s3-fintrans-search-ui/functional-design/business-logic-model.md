# Business Logic Model — S3 Fintrans Search UI

## High-Level Architecture

```
React SPA (Browser)
  |
  +-> SearchForm component
  |     +-> POST /api/search  ──> validates, creates session
  |     +-> GET /api/search/{id}/stream  ──> SSE connection
  |
  +-> ResultsTab component
  |     +-> processes SSE events incrementally
  |     +-> GET /api/search/{id}/results  ──> final report
  |
  +-> HistoryPanel component
  |     +-> GET /api/search/history
  |
  +-> SavedSearches component
        +-> POST /api/saved-searches
        +-> GET /api/saved-searches
        +-> DELETE /api/saved-searches/{id}

FastAPI Backend
  |
  +-> SessionStore (in-memory)
  +-> imports s3_search modules directly
  +-> runs search in background thread
```

---

## API Layer Business Logic

### 1. POST /api/search — Initiate Search

```
Input:  SearchSessionRequest (JSON body)
Output: { "search_id": str } or HTTP error

Logic:
  1. VALIDATE request body:
     - date: must be 'today' or valid YYYYMMDD
     - ids: must be non-empty list of non-empty strings
     - profile: must be non-empty string
     - file_types: each must be in VALID_FILE_TYPES, default ['all']
     - context_lines: must be >= 0, default 3
     IF validation fails: return HTTP 422 with field-level errors

  2. RESOLVE bucket:
     - Call bucket_resolver.resolve_bucket(profile, bucket_override)
     IF AmbiguousProfileError: return HTTP 400 with error message

  3. VALIDATE AWS credentials (synchronous):
     - Call auth.validate_auth(profile)
     IF AuthenticationError: return HTTP 401 with message including
       "Run: aws sso login --profile {profile}"

  4. CREATE session:
     - Generate UUID4
     - Create SearchSession with status=PENDING
     - Store in SessionStore

  5. LAUNCH background search:
     - Start background task (asyncio or thread) to run the search
     - Set session status to RUNNING

  6. RETURN { "search_id": uuid }
```

### 2. GET /api/search/{search_id}/stream — SSE Stream

```
Input:  search_id (path parameter)
Output: SSE event stream (text/event-stream)

Logic:
  1. LOOKUP session in SessionStore
     IF not found: return HTTP 404

  2. OPEN SSE connection

  3. EMIT auth_ok event:
     { "profile": session.request.profile,
       "account": identity_account,
       "arn": identity_arn }

  4. WAIT for discovery to complete, then EMIT discovery event:
     { "files_found": len(files),
       "files": [{"filename": f.filename, "size": f.size} for f in files] }

  5. FOR each file as it completes:
     a. EMIT file_start:
        { "filename": f.filename, "index": i, "total": total }
     b. (file search runs in background thread)
     c. EMIT file_complete:
        { "filename": f.filename,
          "matches": { id: [{"line_number": n, "line_content": s}] },
          "error": error_or_null }

  6. WHEN all files complete:
     a. Aggregate results using search.aggregate_results()
     b. Store report in session
     c. Set session status to COMPLETED
     d. Add to history
     e. EMIT search_complete:
        { "report": report_as_dict }

  7. IF session.cancelled is set at any point:
     a. EMIT cancelled event
     b. Close SSE connection
     c. Set session status to CANCELLED

  8. IF fatal error occurs:
     a. EMIT error event: { "message": str, "code": str }
     b. Set session status to FAILED
     c. Close SSE connection

  9. CLOSE SSE connection after search_complete, cancelled, or error
```

### 3. Background Search Execution

```
Input:  session (SearchSession)
Output: Updates session state in-place, pushes events to an asyncio Queue

Logic:
  event_queue = asyncio.Queue()

  1. DISCOVER files:
     - Call discovery.discover_files(session.boto3_session, bucket, date, file_types)
     IF S3PathNotFoundError:
       event_queue.put(error_event)
       session.status = FAILED
       return
     - session.files_total = len(files)
     - event_queue.put(discovery_event)

  2. SEARCH files in parallel (ThreadPoolExecutor):
     - For each file submitted to executor:
       a. Check session.cancelled — if set, skip remaining files
       b. event_queue.put(file_start_event)
       c. Call search._search_single_file(session.boto3_session, bucket, ids, file)
       d. session.files_completed += 1
       e. session.file_results.append(result)
       f. event_queue.put(file_complete_event)

  3. AGGREGATE results:
     - Build SearchRequest from session params
     - Call search.aggregate_results(request, session.file_results)
     - session.report = report
     - session.status = COMPLETED
     - event_queue.put(search_complete_event)

  4. ADD to history:
     - SessionStore.add_to_history(session)
```

### 4. GET /api/search/{search_id}/results — Final Results

```
Input:  search_id (path parameter)
Output: SearchReport as JSON or HTTP error

Logic:
  1. LOOKUP session in SessionStore
     IF not found: return HTTP 404

  2. IF session.status not in (COMPLETED, CANCELLED):
     return HTTP 409 with { "message": "Search not yet complete", "status": session.status }

  3. IF session.report is None:
     return HTTP 404 with { "message": "No results available" }

  4. RETURN session.report serialized as JSON
     (same structure as CLI --output json)
```

### 5. DELETE /api/search/{search_id} — Cancel Search

```
Input:  search_id (path parameter)
Output: { "cancelled": true } or HTTP error

Logic:
  1. LOOKUP session in SessionStore
     IF not found: return HTTP 404

  2. IF session.status not in (PENDING, RUNNING):
     return HTTP 409 with { "message": "Search is not in progress" }

  3. SET session.cancelled event (threading.Event)
     - Background threads check this flag and stop submitting new files
     - Currently streaming file completes, but no new files are started

  4. RETURN { "cancelled": true }
```

### 6. GET /api/profiles — List Available Profiles

```
Input:  None
Output: list[ProfileInfo]

Logic:
  1. READ ~/.aws/config file
     - Parse all [profile X] sections
     - Extract profile names

  2. READ ~/.aws/credentials file (if exists)
     - Parse all [X] sections
     - Merge with config profiles (union)

  3. FOR each profile name:
     - TRY resolve_bucket(name, None)
       IF success: resolved_bucket = result, is_known = True
       IF AmbiguousProfileError: resolved_bucket = None, is_known = False
       IF no match (fallback used): resolved_bucket = fallback, is_known = False

  4. SORT profiles: known environments first (dev, qa, uat, prod), then alphabetical

  5. RETURN list of ProfileInfo
```

### 7. GET /api/file-types — List Valid File Types

```
Input:  None
Output: list[str]

Logic:
  Return sorted list of VALID_FILE_TYPES from discovery module
  (excluding 'all' — the UI handles 'all' as "no filter selected")
```

### 8. GET /api/search/history — Search History

```
Input:  None
Output: list[SearchHistoryEntry]

Logic:
  Return SessionStore.get_history()
  Ordered by created_at descending (most recent first)
```

### 9. POST /api/search/{search_id}/export — Export Results

```
Input:  search_id (path parameter), format query param ('json' or 'csv')
Output: File download response

Logic:
  1. LOOKUP session in SessionStore
     IF not found: return HTTP 404
     IF not completed: return HTTP 409

  2. IF format == 'json':
     - Serialize report as JSON (same as CLI --output json)
     - Return with Content-Type: application/json
     - Content-Disposition: attachment; filename="search-{date}-{profile}.json"

  3. IF format == 'csv':
     - Generate CSV using same logic as CLI csv renderer
     - Return with Content-Type: text/csv
     - Content-Disposition: attachment; filename="search-{date}-{profile}.csv"
```

### 10. Saved Searches Endpoints

```
POST /api/saved-searches
  Input: { "name": str, "params": SearchSessionRequest }
  Logic: Create SavedSearch with UUID, store in SessionStore
  Output: SavedSearch

GET /api/saved-searches
  Logic: Return SessionStore.get_saved_searches()
  Output: list[SavedSearch]

DELETE /api/saved-searches/{id}
  Logic: Remove from SessionStore
  Output: { "deleted": true } or HTTP 404
```

### 11. Static File Serving

```
Logic:
  Mount React build directory as static files at root "/"
  API routes under "/api/" take precedence
  Fallback: serve index.html for all non-API, non-static routes
    (supports React client-side routing)
```

### 12. Server Startup (s3-search-ui entry point)

```
Input:  --port (default 8080), --no-browser (optional flag)
Output: Running uvicorn server

Logic:
  1. PARSE CLI arguments (port, no-browser flag)
  2. PRINT "S3 Search UI running at http://localhost:{port}"
  3. IF not --no-browser:
     - Open default browser to http://localhost:{port}
       (use webbrowser.open() — non-blocking)
  4. START uvicorn server:
     - uvicorn.run(app, host="0.0.0.0", port=port)
  5. ON Ctrl+C: graceful shutdown
```

---

## Frontend Business Logic

### 13. Search Form Submission Flow

```
User fills form and clicks "Search"
  |
  +-> Client-side validation:
  |     - date: non-empty, matches YYYYMMDD or 'today'
  |     - ids: non-empty (at least one ID after parsing)
  |     - profile: selected from dropdown
  |     IF invalid: show inline error messages, do NOT submit
  |
  +-> Parse IDs from textarea:
  |     - Split by newlines and commas
  |     - Trim whitespace
  |     - Remove empty strings
  |     - Remove duplicates (preserve order)
  |
  +-> POST /api/search with form data
  |     IF 401: show auth error with "aws sso login" hint
  |     IF 422: show validation errors on form fields
  |     IF 400: show error message (ambiguous profile, etc.)
  |     IF 200: receive search_id
  |
  +-> Create new SearchTab with search_id
  +-> Open SSE connection to /api/search/{id}/stream
  +-> Switch to the new tab
```

### 14. SSE Event Processing Flow

```
EventSource connects to /api/search/{id}/stream
  |
  +-> on 'auth_ok':
  |     - Update tab.authInfo
  |     - Set tab.status = 'authenticating' -> 'discovering'
  |
  +-> on 'discovery':
  |     - Update tab.discovery
  |     - Set tab.fileProgress.total = files_found
  |     - Set tab.status = 'searching'
  |
  +-> on 'file_start':
  |     - Update tab.fileProgress.currentFile
  |
  +-> on 'file_complete':
  |     - Increment tab.fileProgress.completed
  |     - Merge matches into tab.results (incrementally build per-ID results)
  |     - If file had error, add to tab.warnings
  |
  +-> on 'search_complete':
  |     - Set tab.report = report
  |     - Set tab.status = 'complete'
  |     - Close EventSource
  |
  +-> on 'cancelled':
  |     - Set tab.status = 'cancelled'
  |     - Close EventSource
  |
  +-> on 'error':
  |     - Set tab.error = message
  |     - Set tab.status = 'error'
  |     - Close EventSource
  |
  +-> on connection error (EventSource onerror):
        - Show reconnect banner
        - Do NOT auto-reconnect (search state may be stale)
```

### 15. Incremental Results Building

```
On each 'file_complete' event:
  FOR each id in event.matches:
    Find or create SearchResult for this id in tab.results
    Append FileMatch with filename, match_count, matching_lines
    Update total_match_count
    Set found = true

  After processing all events:
    IDs not yet seen in any file_complete remain as found=false
    (Final found/not-found is only definitive after search_complete)

Display logic:
  While status == 'searching':
    Show results so far with "searching..." indicator
    IDs with no matches yet show as "pending" (gray), not "not found" (red)
  When status == 'complete':
    Show final results — "not found" is now definitive
```

### 16. Tab Management

```
State: tabs: SearchTab[], activeTabId: string | null

New search:
  - Create tab, add to tabs array, set as active

Switch tab:
  - Set activeTabId to clicked tab's id

Close tab:
  - Remove from tabs array
  - If closed tab was active, switch to previous tab (or first tab)
  - If no tabs remain, show the search form as the main view

Tab label:
  - Format: "{date} / {profile}"
  - If searching: append spinner icon
  - If error: append warning icon
```

### 17. Search History

```
State: history: SearchHistoryEntry[] (in-memory, ordered by created_at desc)

On search_complete:
  - Add entry to history (prepend)

View history:
  - Show in sidebar/dropdown
  - Each entry shows: timestamp, date, profile, "3/5 IDs found"

Re-open from history:
  - GET /api/search/{id}/results
  - Create new tab with status='complete' and the fetched report
  - Tab is read-only (no re-execution)
```

### 18. Saved Searches

```
State: savedSearches: SavedSearch[] (in-memory via API)

Save current form:
  - User clicks "Save Search", enters a name
  - POST /api/saved-searches with name + current form params
  - Add to savedSearches list

Load saved search:
  - User clicks a saved search entry
  - Populate form fields with saved params
  - User can modify and submit

Delete saved search:
  - DELETE /api/saved-searches/{id}
  - Remove from list
```

### 19. Export

```
Export JSON:
  - POST /api/search/{id}/export?format=json
  - Trigger browser file download

Export CSV:
  - POST /api/search/{id}/export?format=csv
  - Trigger browser file download

Available only when tab.status == 'complete'
```
