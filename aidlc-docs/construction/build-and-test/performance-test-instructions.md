# Performance Test Instructions — S3 Fintrans Search UI

## Performance Requirements (from NFR-2)
- SSE streaming shall deliver file-level results within 1 second of each file completing
- The React UI shall render incrementally — no full-page re-renders on each SSE event
- The bundled React build shall be optimized (minified, tree-shaken) for fast initial load
- Multiple concurrent searches (tabs) shall not block each other

## Performance Test Scenarios

### Scenario 1: SSE Latency
- **Objective**: Verify SSE events are delivered within 1 second of file completion
- **Method**: Instrument the executor to log timestamps at file completion and SSE emission
- **Acceptance**: < 1 second latency between file search completion and SSE event delivery

### Scenario 2: Concurrent Searches
- **Objective**: Verify multiple simultaneous searches don't degrade performance
- **Method**: Open 3-5 tabs with concurrent searches against different dates/profiles
- **Acceptance**: Each search completes within expected time (< 60s for 130+ files)

### Scenario 3: Frontend Bundle Size
- **Objective**: Verify the React build is optimized for fast initial load
- **Method**: Check the build output size after `npm run build`
- **Acceptance**: Total bundle size < 500KB gzipped

```bash
# Check bundle size
cd frontend
npm run build
du -sh ../src/s3_search/static/assets/
```

### Scenario 4: API Response Time
- **Objective**: Verify API endpoints respond quickly
- **Method**: Use curl or httpie to measure response times

```bash
# Health check (should be < 10ms)
time curl -s http://localhost:8080/api/health

# Profiles (should be < 500ms, reads filesystem)
time curl -s http://localhost:8080/api/profiles

# File types (should be < 10ms, in-memory)
time curl -s http://localhost:8080/api/file-types
```

## Notes
- Performance testing against real S3 requires valid AWS credentials and network access
- SSE latency is primarily bounded by S3 response time, not the application layer
- The ThreadPoolExecutor concurrency of 10 matches the CLI tool's proven configuration
