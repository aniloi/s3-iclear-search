# Build Instructions — S3 Fintrans Search UI

## Prerequisites
- **Python**: 3.9+
- **Node.js**: 18+ (for frontend build)
- **npm**: 9+ (comes with Node.js)
- **pip**: Latest version
- **AWS CLI**: Configured with at least one profile (for runtime use)

## Build Steps

### 1. Install Python Dependencies (Backend + Dev)

```bash
pip install -e ".[dev]"
```

This installs:
- Existing CLI dependencies (`boto3`)
- UI dependencies (`fastapi`, `uvicorn`, `sse-starlette`, `pydantic`)
- Dev dependencies (`pytest`, `pytest-asyncio`, `httpx`, `pytest-cov`)

### 2. Build Frontend (React SPA)

```bash
cd frontend
npm install
npm run build
```

This:
- Installs React, TypeScript, Vite, Tailwind CSS dependencies
- Compiles TypeScript and builds the production bundle
- Outputs to `src/s3_search/static/` (served by FastAPI at runtime)

### 3. Verify Build Success

```bash
# Check frontend build output exists
ls -la src/s3_search/static/
# Should contain: index.html, assets/ directory

# Check Python package is installed
pip show s3-fintrans-search
# Should show version 2.0.0

# Check entry points
which s3-search
which s3-search-ui
```

### 4. Quick Build (Makefile)

```bash
# Full build (frontend + pip install)
make install

# Or with dev dependencies
make install-dev
```

## Build Artifacts

| Artifact | Location | Description |
|---|---|---|
| Python package | `src/s3_search/` | Installed as editable package |
| Frontend build | `src/s3_search/static/` | Minified React SPA (HTML, JS, CSS) |
| CLI entry point | `s3-search` | Original CLI tool |
| UI entry point | `s3-search-ui` | Web UI server launcher |

## Troubleshooting

### Frontend Build Fails with Node.js Errors
- **Cause**: Node.js version too old
- **Solution**: Upgrade to Node.js 18+: `nvm install 18 && nvm use 18`

### pip install Fails with Missing Dependencies
- **Cause**: System Python missing development headers
- **Solution**: Use a virtual environment: `python -m venv .venv && source .venv/bin/activate`

### Frontend Build Output Missing
- **Cause**: `npm run build` not executed before `pip install`
- **Solution**: Run `make install` which handles the correct order
