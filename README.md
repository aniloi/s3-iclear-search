# S3 ICLEAR Search Tool

CLI tool and web UI that searches AWS S3 ICLEAR_S3 files for payment/account/order identifiers. Replaces the manual process of listing files, streaming each one, and grepping for IDs.

## Quick Start

### Install (CLI only)

```bash
pip install -e .
```

### Install (CLI + Web UI)

```bash
# Build the React frontend and install with UI dependencies
make install

# Or manually:
cd frontend && npm install && npm run build && cd ..
pip install -e ".[ui]"
```

### Launch the Web UI

```bash
s3-search-ui
```

This starts the server at `http://localhost:8080` and opens your browser. Press `Ctrl+C` to stop.

Options:
- `--port 3000` — use a different port
- `--no-browser` — don't open the browser automatically
- `--host 127.0.0.1` — bind to localhost only

### Development Mode (hot reload)

```bash
# Terminal 1: Backend with auto-reload
pip install -e ".[dev]"
uvicorn s3_search.api.app:app --reload --port 8080

# Terminal 2: Frontend with hot module replacement
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173` — the Vite dev server proxies API calls to the backend.

---

## CLI Usage

```bash
# Single ID search
s3-search --date 20260501 --id "FABZ003185-1777650549569-RRKJF" --profile qa

# Multiple IDs
s3-search --date 20260501 --id "ID1,ID2,ID3" --profile qa

# From a file (one ID per line)
s3-search --date 20260501 --id-file payment_ids.txt --profile qa

# Filter to specific file types
s3-search --date 20260501 --id "DWTU000481" --profile qa --file-type fintrans_ira

# JSON output
s3-search --date 20260501 --id "DWTU000481" --profile qa --output json

# CSV output
s3-search --date 20260501 --id "DWTU000481" --profile qa --output csv

# Override bucket
s3-search --date 20260501 --id "DWTU000481" --profile prod --bucket custom.bucket.name

# Suppress context lines
s3-search --date 20260501 --id "DWTU000481" --profile qa --context 0
```

## CLI Parameters

| Parameter | Required | Description |
|---|---|---|
| `--date` | Yes | Date folder to search (`YYYYMMDD` or `today` for current UTC date) |
| `--id` | Yes* | Comma-separated search terms |
| `--id-file` | Yes* | Path to file with one search term per line |
| `--profile` | Yes | AWS CLI profile name (`qa`, `uat`, `prod`, etc.) |
| `--file-type` | No | Filter: `all`, `fintrans`, `fintrans_ira`, `ordertrans`, `accounts_add`, `accounts_change`, `allocation` |
| `--bucket` | No | Override S3 bucket (default: environment-aware based on profile) |
| `--output` | No | Output format: `table` (default), `json`, `csv` |
| `--context` | No | Context lines around matches (default: 3, set 0 to suppress) |

*One of `--id` or `--id-file` is required (mutually exclusive).

---

## Web UI Features

- **Search form** with profile dropdown (auto-detected from `~/.aws/config`), file type multi-select, and ID textarea
- **Real-time streaming** — results appear as each file completes, with a progress bar
- **Multi-tab support** — run multiple searches simultaneously
- **Interactive results table** — sortable, filterable, with expandable rows showing matching CSV lines
- **Search history** — re-open past results from the sidebar
- **Saved searches** — save and reload search parameter presets (session-only)
- **Export** — download results as JSON or CSV

---

## Environment-Aware Bucket Defaults

The tool automatically maps profile names to buckets:

| Profile contains | Default bucket |
|---|---|
| `dev` | `dev.drivewealth.aod` |
| `qa` | `qa.drivewealth.aod` |
| `uat` | `uat.drivewealth.aod` |
| `prod` | `prod.drivewealth.aod` |

If a profile matches multiple keywords, the tool asks you to use `--bucket` explicitly.

## Exit Codes (CLI)

| Code | Meaning |
|---|---|
| 0 | Success (even if no IDs found) |
| 1 | Authentication or configuration error |
| 2 | Invalid arguments |

## Running Tests

```bash
pip install -e ".[dev]"
pytest -v
```

95 tests: 44 CLI + 51 API (runs in < 1 second).

## Makefile Targets

| Target | Description |
|---|---|
| `make install` | Build frontend + install with UI deps |
| `make install-dev` | Build frontend + install with dev deps |
| `make build-frontend` | Build the React frontend only |
| `make test` | Run all tests |
| `make test-backend` | Run API tests only |
| `make test-cli` | Run CLI tests only |
| `make clean` | Remove build artifacts |
