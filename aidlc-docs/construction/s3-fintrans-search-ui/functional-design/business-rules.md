# Business Rules — S3 Fintrans Search UI

## API Layer Rules

### BR-UI-1: Session Lifecycle

- Each search creates a new SearchSession with a UUID4 identifier.
- Sessions transition through states: PENDING → RUNNING → COMPLETED | CANCELLED | FAILED.
- State transitions are one-way — a COMPLETED session cannot return to RUNNING.
- Sessions are stored in-memory and lost on server restart.

### BR-UI-2: Synchronous Auth Validation

- AWS credentials are validated synchronously in `POST /api/search` before returning the search_id.
- If auth fails, the API returns HTTP 401 immediately — no session is created.
- The auth_ok SSE event is still emitted for the frontend to display the authenticated identity.
- **Rationale**: Fail fast on auth errors rather than making the user wait for SSE to discover the failure.

### BR-UI-3: Search Cancellation

- A search can be cancelled via `DELETE /api/search/{search_id}`.
- Cancellation sets a `threading.Event` flag checked by the background search.
- The currently-streaming file completes (cannot interrupt mid-stream), but no new files are submitted.
- After cancellation, partial results are available via `GET /api/search/{id}/results`.
- Cancelled searches are added to history with status=CANCELLED.
- Cancelling an already-completed or already-cancelled search returns HTTP 409.

### BR-UI-4: Concurrent Searches

- Multiple searches can run concurrently (one per tab).
- Each search has its own ThreadPoolExecutor with concurrency=10.
- The SessionStore is thread-safe (uses a lock for mutations).
- No global limit on concurrent searches in V1 (server resources are the natural limit).

### BR-UI-5: Dynamic Profile Detection

- The backend reads `~/.aws/config` and `~/.aws/credentials` to discover available profiles.
- Profile names are extracted from `[profile X]` sections in config and `[X]` sections in credentials.
- The `[default]` profile is included if present.
- For each profile, bucket resolution is attempted using the existing `bucket_resolver` logic.
- Profiles are sorted: known environments (dev, qa, uat, prod) first, then alphabetical.
- If `~/.aws/config` is missing or unreadable, return an empty list with no error.

### BR-UI-6: Request Validation

- All API request validation returns HTTP 422 with structured error details.
- Date validation: must be `today` or exactly 8 digits forming a valid calendar date.
- IDs validation: must be a non-empty list; each ID must be a non-empty string after trimming.
- Profile validation: must be a non-empty string.
- File types validation: each must be in VALID_FILE_TYPES.
- Context lines: must be an integer >= 0.
- Bucket override: if provided, must be a non-empty string.

### BR-UI-7: SSE Connection Lifecycle

- The SSE connection is opened by the client after receiving the search_id.
- The server keeps the connection open until: search_complete, cancelled, or error event is sent.
- After the terminal event, the server closes the SSE connection.
- If the client disconnects before completion, the background search continues to completion (results remain available via GET).
- The client does NOT auto-reconnect on SSE errors — it shows a manual reconnect option.

### BR-UI-8: Export Format Rules

- JSON export produces the same structure as CLI `--output json`.
- CSV export produces the same structure as CLI `--output csv`.
- Export is only available for COMPLETED searches.
- Export uses the context_lines value from the original search request.

### BR-UI-9: History Limits

- History is in-memory, ordered by created_at descending.
- No hard limit on history entries in V1 (bounded by session lifetime).
- History entries include summary data only — full results are fetched on demand via `GET /api/search/{id}/results`.
- History is lost on server restart.

### BR-UI-10: Saved Searches (Session-Only)

- Saved searches store parameter presets, not results.
- Each saved search has a UUID and a user-provided name.
- Names do not need to be unique.
- Saved searches are in-memory and lost on server restart.
- Loading a saved search populates the form but does not auto-submit.

---

## Frontend Rules

### BR-UI-11: Client-Side Validation

- The search form validates all fields before submission.
- Validation runs on blur (per field) and on submit (all fields).
- Error messages appear inline below each field.
- The Submit button is disabled while validation errors exist.
- Validation rules mirror the API rules (fail fast on the client).

### BR-UI-12: ID Parsing from Textarea

- The textarea accepts IDs separated by newlines, commas, or a mix.
- Parsing: split by newlines, then split each line by commas.
- Trim whitespace from each token.
- Remove empty strings.
- Remove duplicates (preserve first occurrence order).
- Lines starting with `#` are treated as comments and skipped (same as CLI --id-file).
- Display the parsed ID count below the textarea: "N IDs detected".

### BR-UI-13: Tab Behavior

- The UI uses a single shared search form (always visible at top or in sidebar).
- Each search submission opens a new results tab.
- Tabs display: "{date} / {profile}" as the label.
- Active tab is highlighted.
- Tabs can be closed individually via an "×" button.
- Closing the last tab shows an empty state with a prompt to start a new search.
- Maximum tabs: no hard limit in V1.

### BR-UI-14: Progress Display Rules

- While status is `connecting` or `authenticating`: show a spinner with "Authenticating..."
- While status is `discovering`: show a spinner with "Discovering files..."
- While status is `searching`: show a progress bar with "{completed}/{total} files ({percentage}%)" and the current filename.
- While status is `complete`: hide progress, show final results.
- While status is `cancelled`: show "Search cancelled" banner with partial results.
- While status is `error`: show error message with details.

### BR-UI-15: Incremental Results Display

- During search, results are displayed as they arrive (per file_complete event).
- IDs that have been found show green checkmark and file list.
- IDs not yet seen in any completed file show as "Pending" (gray) — NOT "Not Found".
- Only after `search_complete` do remaining unfound IDs show as "Not Found" (red).
- **Rationale**: Avoid false negatives while search is still in progress.

### BR-UI-16: Table Interaction Rules

- Sorting: click column header to sort ascending; click again for descending.
- Default sort: by ID (alphabetical ascending).
- Filtering: status filter buttons (All / Found / Not Found) above the table.
- Text search: search box filters the ID column by substring match.
- Expandable rows: click a row to expand/collapse context lines.
- Expanded rows show matching CSV lines grouped by file, with line numbers.

### BR-UI-17: Error Display Rules

- API errors (4xx, 5xx): show in a toast notification or inline error banner.
- Auth errors (401): show prominently with the `aws sso login --profile {profile}` command, styled as a copyable code block.
- SSE connection errors: show a yellow warning banner with a "Reconnect" button (which re-fetches results, not re-runs the search).
- Validation errors: show inline on the form field that failed.
- File-level warnings (access denied, retries exhausted): show in a collapsible warning section above the results table.

### BR-UI-18: Keyboard Accessibility

- All interactive elements are reachable via Tab key.
- Enter key submits the search form.
- Escape key closes modals/dropdowns.
- Arrow keys navigate dropdown options.
- Table rows are expandable via Enter/Space when focused.
- Tab close buttons are keyboard accessible.

### BR-UI-19: CORS and API Routing

- In production (bundled): no CORS needed — same origin (FastAPI serves both API and static files).
- In development: FastAPI enables CORS for `localhost:5173` (Vite dev server default).
- All API routes are prefixed with `/api/`.
- Non-API routes fall through to the React SPA's `index.html` (client-side routing support).
