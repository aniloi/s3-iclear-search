# Domain Entities — S3 ICLEAR Fintrans Search Tool

## Entity Relationship Overview

```
SearchRequest ──> BucketResolver ──> resolved bucket name
     │
     v
AuthValidator ──> boto3 Session
     │
     v
FileDiscovery ──> list of S3FileInfo
     │
     v
SearchEngine (parallel) ──> list of FileSearchResult
     │
     v
ResultAggregator ──> list of SearchResult (per ID)
     │
     v
ReportRenderer ──> SearchReport ──> stdout
```

---

## 1. SearchRequest

Represents the parsed and validated CLI arguments.

```
SearchRequest:
    date: str                    # YYYYMMDD format (resolved from 'today' if needed)
    ids: list[str]               # List of search terms (from --id or --id-file)
    profile: str                 # AWS profile name (always required)
    file_types: list[str]        # Filtered file types, or ['all']
    bucket: str                  # Resolved bucket name (env-aware or explicit override)
    output_format: str           # 'table' | 'json' | 'csv'
    context_lines: int           # Number of context lines (0 = suppress)
    concurrency: int             # Max concurrent S3 streams (default: 10)
```

**Construction**: Built by the argument parser. All validation happens during construction — if a `SearchRequest` exists, it is valid.

---

## 2. BucketResolver

Resolves the default bucket name from the AWS profile name.

```
BucketResolver:
    PROFILE_BUCKET_MAP: dict[str, str]
        'dev'  -> 'dev.drivewealth.aod'
        'qa'   -> 'qa.drivewealth.aod'
        'uat'  -> 'uat.drivewealth.aod'
        'prod' -> 'prod.drivewealth.aod'
    FALLBACK_BUCKET: str = 'qa.drivewealth.aod'

    resolve(profile: str, explicit_bucket: str | None) -> str:
        If explicit_bucket is provided, return it directly.
        Count how many keywords from PROFILE_BUCKET_MAP match the profile name.
        If exactly 1 match: return the corresponding bucket.
        If 0 matches: return FALLBACK_BUCKET.
        If >1 matches: raise AmbiguousProfileError with message listing
            the conflicting keywords and suggesting --bucket.
```

---

## 3. S3FileInfo

Metadata about a single file discovered in S3.

```
S3FileInfo:
    key: str                     # Full S3 object key
    filename: str                # Just the filename portion (after last '/')
    size: int                    # File size in bytes
```

---

## 4. FileSearchResult

Result of searching a single file for all IDs.

```
FileSearchResult:
    file: S3FileInfo
    matches: dict[str, list[MatchLine]]   # ID -> list of matching lines
    error: str | None                      # Error message if file failed
    retries_used: int                      # Number of retries before success/failure
```

---

## 5. MatchLine

A single matching line within a file.

```
MatchLine:
    line_number: int             # 1-based line number in the file
    line_content: str            # Full CSV row content (stripped of newline)
```

---

## 6. SearchResult

Aggregated result for a single search ID across all files.

```
SearchResult:
    id: str                      # The search term
    found: bool                  # True if at least one match exists
    file_matches: list[FileMatch]  # All files where this ID was found
    total_match_count: int       # Total matches across all files
```

---

## 7. FileMatch

Matches for a specific ID within a specific file.

```
FileMatch:
    filename: str                # The file where matches were found
    match_count: int             # Number of matches in this file
    matching_lines: list[MatchLine]  # All matching CSV rows
```

---

## 8. SearchReport

The final output model containing everything needed to render results.

```
SearchReport:
    date: str                    # Search date
    bucket: str                  # Bucket searched
    profile: str                 # AWS profile used
    files_searched: int          # Total files searched
    files_failed: int            # Files that failed (after retries)
    warnings: list[str]          # Warning messages (skipped files, access denied)
    results: list[SearchResult]  # Per-ID results
    summary: SearchSummary
```

---

## 9. SearchSummary

```
SearchSummary:
    total_ids: int               # Total IDs searched for
    found_count: int             # IDs found in at least one file
    not_found_count: int         # IDs not found in any file
```

---

## 10. Custom Exceptions

```
AuthenticationError:
    profile: str
    message: str
    # Raised when STS get_caller_identity fails

AmbiguousProfileError:
    profile: str
    matching_keywords: list[str]
    # Raised when profile matches multiple environment keywords

S3PathNotFoundError:
    bucket: str
    date: str
    # Raised when the ICLEAR_S3 path doesn't exist or is empty

FileStreamError:
    filename: str
    attempt: int
    cause: str
    # Raised on S3 streaming failure (used internally for retry logic)
```

---

## 11. Known File Type Registry

```
FILE_TYPE_PATTERNS: dict[str, str]
    'fintrans'        -> 'fintrans_'        (but NOT 'fintrans_ira')
    'fintrans_ira'    -> 'fintrans_ira_'
    'ordertrans'      -> 'ordertrans_'
    'accounts_add'    -> 'accounts_add_'
    'accounts_change' -> 'accounts_change_'
    'allocation'      -> 'Allocation_'

VALID_FILE_TYPES: set[str] = keys of FILE_TYPE_PATTERNS + {'all'}
```

**Matching logic**: For `fintrans`, the pattern `fintrans_` matches but `fintrans_ira_` is excluded by checking that `fintrans_ira_` does NOT appear in the filename. This ensures `--file-type fintrans` returns only regular fintrans files, not IRA ones.
