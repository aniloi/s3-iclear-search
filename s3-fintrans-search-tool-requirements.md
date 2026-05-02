# S3 ICLEAR Fintrans Search Tool — Requirements Document

## Purpose

CLI tool that searches AWS S3 ICLEAR_S3 files for payment/account/order identifiers. Replaces a manual process of listing files, streaming each one, and grepping for IDs.

---

## Usage

```bash
# Single ID search
s3-search --date 20260501 --id "FABZ003185-1777650549569-RRKJF" --profile qa

# Multiple IDs
s3-search --date 20260501 --id "ID1,ID2,ID3" --profile qa

# From a file (one ID per line)
s3-search --date 20260501 --id-file payment_ids.txt --profile qa

# Filter to specific file types
s3-search --date 20260501 --id "DWTU000481" --profile qa --file-type fintrans_ira

# Search all file types (default)
s3-search --date 20260501 --id "DWTU000481" --profile qa --file-type all
```

---

## Inputs

| Parameter | Required | Description |
|---|---|---|
| `--date` | Yes | Date folder to search, format `YYYYMMDD` (e.g., `20260501`). Supports `today` as a shorthand for the current UTC date. |
| `--id` | Yes (or `--id-file`) | One or more search terms, comma-separated. Can be a paymentID (`FABZ003185-1777650549569-RRKJF`), accountID (`DWTU000481`), FinTranID (`NE.fb7227cc-f77b-4411-ba51-a285d6bd0aea`), orderID, or any arbitrary string. |
| `--id-file` | Yes (or `--id`) | Path to a text file with one search term per line. Blank lines and lines starting with `#` are ignored. |
| `--profile` | Yes | AWS CLI profile name to use (e.g., `qa`, `uat`, `prod`). |
| `--file-type` | No | Filter which file types to search. Options: `all` (default), `fintrans`, `fintrans_ira`, `ordertrans`, `accounts_add`, `accounts_change`, `allocation`. Comma-separated for multiple. |
| `--bucket` | No | Override the S3 bucket. Default: `qa.drivewealth.aod`. |
| `--output` | No | Output format: `table` (default), `json`, `csv`. |
| `--context` | No | Number of characters to show around each match for context. Default: `200`. Set to `0` to suppress context. |

---

## S3 Bucket Structure

```
s3://{bucket}/{date}/ICLEAR_S3/
```

### Known file type prefixes

These are the file name patterns observed in the bucket. The tool should discover files dynamically (not hardcode these), but this documents what exists:

| File Pattern | Description |
|---|---|
| `DRVW_INTE_transactions_fintrans_{daterange}_part{N}.csv` | Regular financial transactions |
| `DRVW_INTE_transactions_fintrans_ira_{daterange}_part{N}.csv` | IRA-specific financial transactions |
| `DRVW_INTE_transactions_ordertrans_{daterange}_part{N}.csv` | Order transactions |
| `DRVW_INTE_uas_accounts_add_{daterange}_part{N}.csv` | New account records |
| `DRVW_INTE_uas_accounts_change_{daterange}_part{N}.csv` | Account change records |
| `QAAE_Allocation_{daterange}_part{N}.csv` | Allocation records |

Where `{daterange}` is like `202605010700-202605010715` (start-end UTC timestamps).

---

## Behavior

### Step 1 — Validate AWS auth

Before searching, verify the AWS profile is authenticated:

```bash
aws sts get-caller-identity --profile {profile}
```

If this fails (expired token, etc.), print a clear error message telling the user to run `aws sso login --profile {profile}` and exit with a non-zero code.

### Step 2 — List all files in the date/ICLEAR_S3 path

```bash
aws s3 ls s3://{bucket}/{date}/ICLEAR_S3/ --profile {profile}
```

- If the path doesn't exist or returns empty, print an error: `No files found for date {date} in bucket {bucket}`.
- Apply `--file-type` filter if provided (substring match on filename).
- Sort files by their timestamp range (already natural sort order from S3 listing).
- Print a summary: `Found {N} files to search`.

### Step 3 — Search files in parallel

For each file:
1. Stream the file content from S3 (do NOT download to disk): `aws s3 cp s3://.../{file} -`
2. Search the content for each ID (simple substring match, case-sensitive).
3. If a match is found, record: `{id}`, `{filename}`, and optionally a snippet of context around the match.

**Parallelism**: Search multiple files concurrently to speed things up. Use a configurable concurrency limit (default: 10 concurrent streams). Files can be large (up to ~1.4MB observed), so streaming is preferred over downloading.

### Step 4 — Report results

Print a summary table:

```
Search Results for date: 20260501
Bucket: qa.drivewealth.aod
Profile: qa
Files searched: 131

ID                                          | Found | File(s)
--------------------------------------------|-------|--------
FABZ003185-1777650549569-RRKJF              | ✅    | fintrans_ira_...1145-1200_part1.csv
FANF003208-1777650549298-RGHAD              | ✅    | fintrans_ira_...1145-1200_part1.csv
DWTU000481-1777650550283-DIJTX              | ❌    | —
NE.fb7227cc-f77b-4411-ba51-a285d6bd0aea     | ❌    | —

Summary: 2/4 IDs found
```

If `--context` is non-zero, show a snippet of the matching row for each hit (truncated to `--context` characters).

If `--output json`, return:

```json
{
  "date": "20260501",
  "bucket": "qa.drivewealth.aod",
  "profile": "qa",
  "filesSearched": 131,
  "results": [
    {
      "id": "FABZ003185-1777650549569-RRKJF",
      "found": true,
      "files": [
        {
          "filename": "DRVW_INTE_transactions_fintrans_ira_202605011145-202605011200_part1.csv",
          "matchCount": 1,
          "context": "...snippet of matching row..."
        }
      ]
    }
  ],
  "summary": {
    "total": 4,
    "found": 2,
    "notFound": 2
  }
}
```

---

## Edge Cases and Error Handling

| Scenario | Expected Behavior |
|---|---|
| AWS token expired | Print clear error with `aws sso login` command to run. Exit code 1. |
| Date folder doesn't exist in S3 | Print error: `No ICLEAR_S3 folder found for date {date}`. Exit code 1. |
| No files match `--file-type` filter | Print warning: `No files matching type '{type}' found`. Exit code 0. |
| ID found in multiple files | List all files where it was found. |
| Very large file (>10MB) | Still stream — do not load entire file into memory at once. Use line-by-line or chunked reading. |
| S3 access denied on a specific file | Log a warning for that file, continue searching remaining files. |
| Empty `--id` list | Print usage help and exit. |
| Special characters in ID (dots, dashes, UUIDs) | Treat as literal substring match. No regex interpretation. |

---

## Non-Functional Requirements

- **Language**: Python 3.9+ (no external dependencies beyond `boto3` and standard library). Alternatively, a shell script wrapping `aws s3 cp` with `grep` is acceptable if performance is adequate.
- **Performance**: Parallel file streaming. Searching 130+ files should complete in under 60 seconds.
- **No disk writes**: Stream S3 files to memory/stdout, do not create temp files.
- **Portable**: Should work on macOS and Linux. Uses the user's existing AWS CLI configuration and profiles.
- **Exit codes**: `0` = success (even if no IDs found), `1` = auth/config error, `2` = invalid arguments.

---

## Nice-to-Haves (Not Required for V1)

- **Progress bar** showing files searched / total.
- **Caching**: If the same date is searched multiple times, cache the file listing (not contents).
- **Date range search**: `--date 20260501-20260503` to search across multiple days.
- **Regex mode**: `--regex` flag to treat `--id` as a regex pattern instead of literal substring.
- **Allure integration**: `--launch-id 63239` flag that automatically extracts paymentIDs from an Allure TestOps launch before searching S3 (using the REST API pattern documented below).

---

## Appendix: Allure TestOps PaymentID Extraction (for future integration)

If building the Allure integration, here's how to extract paymentIDs from a launch:

1. **Auth**: Use `Authorization: Api-Token {token}` header (NOT Bearer). Token is in `$ALLURE_TOKEN` env var.
2. **Base URL**: `https://drivewealth.testops.cloud`
3. **Get passed test results**:
   ```
   GET /api/rs/testresult?launchId={launchId}&page=0&pageSize=200
   ```
   Filter locally for `status == "passed"`. Paginate if `totalPages > 1`.
4. **Get execution steps for each result**:
   ```
   GET /api/rs/testresult/{testResultId}/execution
   ```
   This returns the step tree with substeps.
5. **Extract paymentIDs**: Walk all steps/substeps recursively. Look for:
   - `"paymentID with expected value: {id}"` in step names
   - `"paymentID": "{id}"` in JSON content within step names
6. **Deduplicate** the collected paymentIDs before passing to the S3 search.
