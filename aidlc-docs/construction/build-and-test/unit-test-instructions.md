# Unit Test Execution — S3 Fintrans Search UI

## Run All Unit Tests

```bash
pytest -v
```

### Expected Results
- **Total tests**: 95
- **Expected**: 95 pass, 0 failures
- **Execution time**: < 2 seconds

## Test Breakdown

### CLI Tests (44 tests — existing, unchanged)

| Test File | Tests | Description |
|---|---|---|
| `tests/test_auth.py` | 3 | AWS authentication validation |
| `tests/test_bucket_resolver.py` | 9 | Profile-to-bucket resolution |
| `tests/test_cli.py` | 12 | CLI argument parsing and validation |
| `tests/test_discovery.py` | 4 | S3 file discovery |
| `tests/test_models.py` | 6 | Domain entity construction |
| `tests/test_renderers.py` | 5 | Output rendering (table, JSON, CSV) |
| `tests/test_search.py` | 3 | Parallel file search engine |

```bash
# Run CLI tests only
pytest -v tests/test_auth.py tests/test_bucket_resolver.py tests/test_cli.py tests/test_discovery.py tests/test_models.py tests/test_renderers.py tests/test_search.py
```

### API Tests (51 tests — new)

| Test File | Tests | Description |
|---|---|---|
| `tests/test_api_models.py` | 23 | Pydantic model validation, SearchSession, SessionStore |
| `tests/test_api_profiles.py` | 8 | AWS profile detection from config files |
| `tests/test_api_executor.py` | 5 | Background search executor with SSE events |
| `tests/test_api_app.py` | 15 | FastAPI endpoint tests (health, search, cancel, history, saved searches) |

```bash
# Run API tests only
pytest -v tests/test_api_models.py tests/test_api_profiles.py tests/test_api_executor.py tests/test_api_app.py
```

## Test Coverage

```bash
pytest --cov=s3_search --cov-report=term-missing -v
```

## Fix Failing Tests

If tests fail:
1. Review the test output for the specific assertion error
2. Check if the failure is in CLI tests (existing code) or API tests (new code)
3. For API tests, verify that `fastapi`, `pydantic`, and `sse-starlette` are installed: `pip install -e ".[dev]"`
4. Rerun the specific failing test: `pytest -v tests/test_file.py::test_name`
