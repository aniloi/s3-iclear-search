# Integration Test Instructions — S3 Fintrans Search UI

## Purpose
Test the end-to-end flow from the FastAPI API through the existing search modules to verify the integration layer works correctly.

## Test Scenarios

### Scenario 1: API → Search Module Integration
- **Description**: Verify that `POST /api/search` correctly creates a session and the SSE stream produces valid events by calling the real search modules (with mocked S3).
- **Covered by**: `tests/test_api_executor.py` — tests the executor with mocked `discover_files` and `_search_single_file`, verifying the full event sequence (auth_ok → discovery → file_complete → search_complete).

### Scenario 2: API → Profile Detection Integration
- **Description**: Verify that `GET /api/profiles` correctly reads AWS config files and resolves buckets using the real `bucket_resolver` module.
- **Covered by**: `tests/test_api_profiles.py` — tests with mocked `~/.aws/config` files, verifying profile parsing and bucket resolution.

### Scenario 3: API → Session Store Integration
- **Description**: Verify that search sessions are correctly created, tracked, cancelled, and added to history through the full API flow.
- **Covered by**: `tests/test_api_app.py` — tests the full HTTP request/response cycle through FastAPI TestClient.

### Scenario 4: Frontend → Backend Integration (Manual)
- **Description**: Verify the React SPA communicates correctly with the FastAPI backend.
- **Setup**: Requires both servers running and valid AWS credentials.

#### Manual Integration Test Steps

```bash
# Terminal 1: Start backend
pip install -e ".[dev]"
uvicorn s3_search.api.app:app --reload --port 8080

# Terminal 2: Start frontend dev server
cd frontend && npm install && npm run dev
```

1. Open `http://localhost:5173` in a browser
2. Verify the profile dropdown loads (calls `GET /api/profiles`)
3. Verify file types load (calls `GET /api/file-types`)
4. Fill in the search form with valid parameters
5. Submit and verify:
   - SSE connection opens
   - Progress bar updates
   - Results appear incrementally
   - Final results table is interactive (sort, filter, expand)
6. Test cancellation: start a search, click Cancel
7. Test history: verify completed searches appear in the sidebar
8. Test export: click Export JSON / Export CSV on completed results

### Scenario 5: Production Bundle Integration (Manual)

```bash
# Build and install
make install

# Run the production server
s3-search-ui --port 8080

# Verify:
# - Browser opens automatically
# - React SPA loads from FastAPI static files
# - All functionality works as in dev mode
```

## Automated Integration Test Coverage

The following integration paths are covered by automated tests:

| Path | Test File | Status |
|---|---|---|
| API → SearchSession lifecycle | `test_api_app.py` | ✅ Automated |
| API → Auth validation | `test_api_app.py` | ✅ Automated |
| API → Bucket resolution | `test_api_app.py` | ✅ Automated |
| Executor → Discovery + Search | `test_api_executor.py` | ✅ Automated |
| Profile detection → Config parsing | `test_api_profiles.py` | ✅ Automated |
| Frontend → Backend (full flow) | Manual | 🔧 Manual |
| Production bundle serving | Manual | 🔧 Manual |
