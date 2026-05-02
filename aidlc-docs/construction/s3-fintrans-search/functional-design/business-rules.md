# Business Rules — S3 ICLEAR Fintrans Search Tool

## BR-1: Profile is Always Required

- The `--profile` parameter must always be provided.
- The tool never falls back to the default AWS credential chain.
- **Rationale**: Prevents accidental use of wrong credentials in a multi-environment setup.

## BR-2: Mutual Exclusivity of ID Sources

- `--id` and `--id-file` are mutually exclusive.
- Exactly one must be provided.
- If both are provided → exit code 2.
- If neither is provided → exit code 2.

## BR-3: Environment-Aware Bucket Resolution

- Profile names are matched against known environment keywords: `dev`, `qa`, `uat`, `prod`.
- Matching is case-insensitive substring match against the profile name.
- If exactly one keyword matches → use the corresponding bucket.
- If zero keywords match → use fallback bucket (`qa.drivewealth.aod`).
- If multiple keywords match → reject with error, suggest `--bucket`.
- Explicit `--bucket` always overrides the environment-aware default.

### Bucket Mapping Table

| Keyword | Bucket |
|---|---|
| `dev` | `dev.drivewealth.aod` |
| `qa` | `qa.drivewealth.aod` |
| `uat` | `uat.drivewealth.aod` |
| `prod` | `prod.drivewealth.aod` |

## BR-4: Date Resolution

- `today` resolves to the current **UTC** date in `YYYYMMDD` format.
- All other date values must be exactly 8 digits and represent a valid calendar date.
- Invalid dates → exit code 2.

## BR-5: File Type Filtering (Exact Keyword Match)

- Only the documented file type keywords are accepted: `fintrans`, `fintrans_ira`, `ordertrans`, `accounts_add`, `accounts_change`, `allocation`, `all`.
- Unknown keywords → exit code 2 with list of valid options.
- `all` means no filtering (search all files).
- If `all` appears with other types, treat as `all`.
- Special disambiguation: `fintrans` must NOT match `fintrans_ira` files. The filter checks for the presence of the type's pattern string AND the absence of more specific patterns.

## BR-6: Literal Substring Matching

- Search IDs are matched as literal substrings within each CSV line.
- Matching is **case-sensitive**.
- No regex interpretation — dots, dashes, brackets, and other special characters are treated literally.
- Each line is checked against every search ID independently.

## BR-7: Line-Based Context Display

- Context shows full CSV rows where matches were found.
- `--context N` controls how many context lines are shown (default: 3).
- `--context 0` suppresses all context output.
- All matching lines are recorded internally; the `--context` parameter only affects display.
- In table output, context lines are indented below the result row.
- In JSON output, context is an array of line strings.
- In CSV output, context lines are joined with ` | ` separator and CSV-escaped.

## BR-8: Compressed File Exclusion

- Files ending in `.gz`, `.zip`, `.bz2`, or other compression extensions are silently skipped during file discovery.
- No warning is printed for skipped compressed files.

## BR-9: Retry Policy for S3 Streaming

- Each file gets up to 3 attempts (1 initial + 2 retries).
- Backoff schedule: 2 seconds after first failure, 4 seconds after second failure.
- After 3 failures, the file is skipped with a warning message.
- Access denied errors are NOT retried — they fail immediately with a warning.
- Warnings for failed files are collected and displayed in the output.

## BR-10: ANSI Color Output

- ANSI color codes are used for terminal output:
  - Green (`\033[32m`) for found indicators (✅)
  - Red (`\033[31m`) for not-found indicators (❌)
  - Yellow (`\033[33m`) for warnings (⚠)
  - Reset (`\033[0m`) after each colored segment
- Color is automatically disabled when stdout is not a TTY (piped to file or another command).
- Detection: `sys.stdout.isatty()`.

## BR-11: Exit Code Rules

| Condition | Exit Code |
|---|---|
| Search completed successfully (regardless of whether IDs were found) | 0 |
| Authentication failure (expired token, invalid profile, etc.) | 1 |
| S3 path not found (date folder doesn't exist) | 1 |
| Invalid arguments (bad date, both --id and --id-file, unknown file type, etc.) | 2 |
| No files match file-type filter | 0 (with warning) |
| Some files failed but search completed | 0 (with warnings) |

## BR-12: ID File Parsing Rules

- Read line-by-line from the specified file path.
- Strip leading and trailing whitespace from each line.
- Skip lines that are empty after stripping.
- Skip lines where the first non-whitespace character is `#`.
- If the file does not exist or cannot be read → exit code 2.
- If parsing produces zero IDs → exit code 2.

## BR-13: Concurrency Limit

- Default concurrency: 10 concurrent S3 streams.
- This is an internal default, not exposed as a CLI parameter in V1.
- Each thread creates its own S3 client from the shared session to ensure thread safety.

## BR-14: Memory Management

- Files are streamed line-by-line; no file is ever fully loaded into memory.
- Match results (MatchLine objects) are accumulated in memory — this is acceptable because matches are expected to be sparse relative to file size.
- No temporary files are created on disk.
