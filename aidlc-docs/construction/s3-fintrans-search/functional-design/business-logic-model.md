# Business Logic Model — S3 ICLEAR Fintrans Search Tool

## High-Level Flow

```
main()
  |
  +-> parse_and_validate_args()        [Step 1: Argument Parsing]
  |     +-> resolve_date()
  |     +-> resolve_ids()
  |     +-> resolve_bucket()
  |     +-> validate_file_types()
  |     => SearchRequest
  |
  +-> validate_auth(request)           [Step 2: Auth Validation]
  |     +-> boto3.Session(profile)
  |     +-> sts.get_caller_identity()
  |     => boto3 Session (or exit 1)
  |
  +-> discover_files(session, request) [Step 3: File Discovery]
  |     +-> s3.list_objects_v2()
  |     +-> filter_by_file_type()
  |     +-> filter_compressed_files()
  |     => list[S3FileInfo] (or exit 1)
  |
  +-> search_files(session, request,   [Step 4: Parallel Search]
  |               files)
  |     +-> ThreadPoolExecutor(max=10)
  |     +-> search_single_file() x N
  |     +-> retry_with_backoff()
  |     => list[FileSearchResult]
  |
  +-> aggregate_results(request,       [Step 5: Aggregation]
  |                     file_results)
  |     => SearchReport
  |
  +-> render_report(request, report)   [Step 6: Output]
        +-> render_table() | render_json() | render_csv()
        => stdout
```

---

## Step 1: Argument Parsing — `parse_and_validate_args()`

### 1.1 Date Resolution — `resolve_date(date_str)`

```
Input:  date_str (from --date)
Output: str in YYYYMMDD format

Logic:
  IF date_str == 'today':
    return datetime.utcnow().strftime('%Y%m%d')
  ELSE:
    Validate format matches YYYYMMDD (8 digits, valid date)
    IF invalid: print error, exit(2)
    return date_str
```

### 1.2 ID Resolution — `resolve_ids(id_arg, id_file_arg)`

```
Input:  id_arg (from --id, may be None)
        id_file_arg (from --id-file, may be None)
Output: list[str] of search IDs

Logic:
  IF both id_arg and id_file_arg provided:
    print error: "Cannot use both --id and --id-file"
    exit(2)
  IF neither provided:
    print usage help
    exit(2)
  IF id_arg:
    Split by comma, strip whitespace from each
    Remove empty strings
    IF empty list: print error, exit(2)
    return list
  IF id_file_arg:
    IF file does not exist: print error, exit(2)
    Read file line-by-line
    Strip whitespace from each line
    Skip blank lines
    Skip lines starting with '#'
    IF empty list: print error "No IDs found in file", exit(2)
    return list
```

### 1.3 Bucket Resolution — `resolve_bucket(profile, explicit_bucket)`

```
Input:  profile (from --profile)
        explicit_bucket (from --bucket, may be None)
Output: str bucket name

Logic:
  Delegate to BucketResolver.resolve()
  (See domain-entities.md for BucketResolver logic)
  IF AmbiguousProfileError raised:
    print error with conflicting keywords and --bucket suggestion
    exit(2)
```

### 1.4 File Type Validation — `validate_file_types(file_type_arg)`

```
Input:  file_type_arg (from --file-type, default 'all')
Output: list[str] of validated file type keywords

Logic:
  Split by comma, strip whitespace, lowercase
  FOR each type:
    IF type not in VALID_FILE_TYPES:
      print error listing valid options
      exit(2)
  IF 'all' in list:
    return ['all']
  return list
```

---

## Step 2: Auth Validation — `validate_auth(request)`

```
Input:  request.profile
Output: boto3.Session (authenticated)

Logic:
  TRY:
    session = boto3.Session(profile_name=request.profile)
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    Print: "Authenticated as {identity['Arn']}"
    return session
  CATCH (BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound):
    print to stderr:
      "Authentication failed for profile '{profile}'.
       Run: aws sso login --profile {profile}"
    exit(1)
```

---

## Step 3: File Discovery — `discover_files(session, request)`

```
Input:  session (boto3.Session)
        request (SearchRequest)
Output: list[S3FileInfo]

Logic:
  s3 = session.client('s3')
  prefix = f"{request.date}/ICLEAR_S3/"
  all_files = []

  # Paginate through list_objects_v2
  paginator = s3.get_paginator('list_objects_v2')
  FOR page IN paginator.paginate(Bucket=request.bucket, Prefix=prefix):
    IF 'Contents' not in page:
      continue
    FOR obj IN page['Contents']:
      key = obj['Key']
      filename = key.split('/')[-1]
      IF filename is empty: continue  # skip "directory" markers
      IF filename ends with '.gz': continue  # skip compressed files
      all_files.append(S3FileInfo(key=key, filename=filename, size=obj['Size']))

  IF all_files is empty:
    print to stderr: "No ICLEAR_S3 folder found for date {request.date}"
    exit(1)

  # Apply file-type filter
  IF request.file_types != ['all']:
    filtered = filter_by_file_type(all_files, request.file_types)
    IF filtered is empty:
      types_str = ', '.join(request.file_types)
      print to stderr: "No files matching type '{types_str}' found"
      exit(0)
    all_files = filtered

  Print: "Found {len(all_files)} files to search"
  return all_files
```

### 3.1 File Type Filtering — `filter_by_file_type(files, file_types)`

```
Input:  files (list[S3FileInfo])
        file_types (list[str])
Output: list[S3FileInfo]

Logic:
  result = []
  FOR file IN files:
    FOR ft IN file_types:
      pattern = FILE_TYPE_PATTERNS[ft]
      IF pattern in file.filename:
        # Special case: 'fintrans' should NOT match 'fintrans_ira'
        IF ft == 'fintrans' AND 'fintrans_ira' in file.filename:
          continue
        result.append(file)
        break  # avoid duplicates if file matches multiple types
  return result
```

---

## Step 4: Parallel Search — `search_files(session, request, files)`

```
Input:  session (boto3.Session)
        request (SearchRequest)
        files (list[S3FileInfo])
Output: list[FileSearchResult]

Logic:
  results = []
  WITH ThreadPoolExecutor(max_workers=request.concurrency) as executor:
    futures = {
      executor.submit(search_single_file, session, request, file): file
      FOR file IN files
    }
    FOR future IN as_completed(futures):
      result = future.result()
      results.append(result)
  return results
```

### 4.1 Single File Search — `search_single_file(session, request, file)`

```
Input:  session, request, file (S3FileInfo)
Output: FileSearchResult

Logic:
  FOR attempt IN range(1, 4):  # up to 3 attempts
    TRY:
      s3 = session.client('s3')
      response = s3.get_object(Bucket=request.bucket, Key=file.key)
      body = response['Body']

      matches: dict[str, list[MatchLine]] = {id: [] for id in request.ids}
      line_number = 0

      FOR line_bytes IN body.iter_lines():
        line_number += 1
        line = line_bytes.decode('utf-8', errors='replace').rstrip('\n').rstrip('\r')
        FOR id IN request.ids:
          IF id in line:  # literal substring, case-sensitive
            matches[id].append(MatchLine(line_number=line_number, line_content=line))

      body.close()

      # Remove IDs with no matches
      matches = {id: lines for id, lines in matches.items() if lines}

      return FileSearchResult(
        file=file,
        matches=matches,
        error=None,
        retries_used=attempt - 1
      )

    CATCH (ClientError) as e:
      IF e.response['Error']['Code'] == 'AccessDenied':
        return FileSearchResult(
          file=file, matches={}, error=f"Access denied: {file.filename}",
          retries_used=attempt - 1
        )
      IF attempt < 3:
        sleep(2 ** attempt)  # exponential backoff: 2s, 4s
        continue
      return FileSearchResult(
        file=file, matches={}, error=f"Failed after 3 retries: {file.filename}: {e}",
        retries_used=attempt - 1
      )

    CATCH (Exception) as e:
      IF attempt < 3:
        sleep(2 ** attempt)
        continue
      return FileSearchResult(
        file=file, matches={}, error=f"Failed after 3 retries: {file.filename}: {e}",
        retries_used=attempt - 1
      )
```

**Note on `iter_lines()`**: boto3's `StreamingBody` does not have `iter_lines()` natively. The implementation will wrap the streaming body to read line-by-line using a buffered reader approach (e.g., `io.TextIOWrapper` or manual chunk-based line splitting).

---

## Step 5: Result Aggregation — `aggregate_results(request, file_results)`

```
Input:  request (SearchRequest)
        file_results (list[FileSearchResult])
Output: SearchReport

Logic:
  warnings = []
  files_failed = 0

  # Collect warnings from failed files
  FOR fr IN file_results:
    IF fr.error is not None:
      warnings.append(fr.error)
      files_failed += 1

  # Aggregate per-ID results
  id_results: dict[str, SearchResult] = {}
  FOR id IN request.ids:
    file_matches = []
    total_count = 0
    FOR fr IN file_results:
      IF id IN fr.matches:
        lines = fr.matches[id]
        file_matches.append(FileMatch(
          filename=fr.file.filename,
          match_count=len(lines),
          matching_lines=lines
        ))
        total_count += len(lines)
    id_results[id] = SearchResult(
      id=id,
      found=len(file_matches) > 0,
      file_matches=file_matches,
      total_match_count=total_count
    )

  # Build summary
  found_count = sum(1 for r in id_results.values() if r.found)
  summary = SearchSummary(
    total_ids=len(request.ids),
    found_count=found_count,
    not_found_count=len(request.ids) - found_count
  )

  return SearchReport(
    date=request.date,
    bucket=request.bucket,
    profile=request.profile,
    files_searched=len(file_results) - files_failed,
    files_failed=files_failed,
    warnings=warnings,
    results=list(id_results.values()),
    summary=summary
  )
```

---

## Step 6: Output Rendering — `render_report(request, report)`

### 6.1 Table Renderer — `render_table(report, context_lines)`

```
Logic:
  Print header:
    "Search Results for date: {report.date}"
    "Bucket: {report.bucket}"
    "Profile: {report.profile}"
    "Files searched: {report.files_searched}"
    IF report.files_failed > 0:
      "Files failed: {report.files_failed}"
    blank line

  Print warnings (if any) in yellow:
    FOR warning IN report.warnings:
      "⚠  {warning}"
    blank line

  Print results table:
    Header: "ID | Found | File(s)"
    Separator line

    FOR result IN report.results:
      found_indicator = green "✅" if result.found else red "❌"
      IF result.found:
        filenames = ', '.join(fm.filename for fm in result.file_matches)
        Print: "{result.id} | {found_indicator} | {filenames}"
        IF context_lines > 0:
          FOR fm IN result.file_matches:
            FOR ml IN fm.matching_lines:
              Print (indented): "  Line {ml.line_number}: {ml.line_content}"
      ELSE:
        Print: "{result.id} | {found_indicator} | —"

  Print summary:
    blank line
    "Summary: {report.summary.found_count}/{report.summary.total_ids} IDs found"

  ANSI color handling:
    IF stdout is a TTY: use ANSI escape codes for green/red/yellow
    ELSE (piped): use plain text (no escape codes)
```

### 6.2 JSON Renderer — `render_json(report, context_lines)`

```
Logic:
  Build dict:
    {
      "date": report.date,
      "bucket": report.bucket,
      "profile": report.profile,
      "filesSearched": report.files_searched,
      "filesFailed": report.files_failed,
      "warnings": report.warnings,
      "results": [
        {
          "id": result.id,
          "found": result.found,
          "totalMatchCount": result.total_match_count,
          "files": [
            {
              "filename": fm.filename,
              "matchCount": fm.match_count,
              "context": [ml.line_content for ml in fm.matching_lines]
                         if context_lines > 0 else []
            }
            FOR fm IN result.file_matches
          ]
        }
        FOR result IN report.results
      ],
      "summary": {
        "total": report.summary.total_ids,
        "found": report.summary.found_count,
        "notFound": report.summary.not_found_count
      }
    }
  Print json.dumps(dict, indent=2)
```

### 6.3 CSV Renderer — `render_csv(report, context_lines)`

```
Logic:
  Print header: "id,found,filename,matchCount,context"
  FOR result IN report.results:
    IF result.found:
      FOR fm IN result.file_matches:
        context_str = ""
        IF context_lines > 0 AND fm.matching_lines:
          # Join first N matching lines with ' | ' separator
          context_str = ' | '.join(ml.line_content for ml in fm.matching_lines)
          # CSV-escape: wrap in quotes, double any internal quotes
          context_str = csv_escape(context_str)
        Print: "{result.id},true,{fm.filename},{fm.match_count},{context_str}"
    ELSE:
      Print: "{result.id},false,,,0,"
```
