"""S3 file discovery and filtering."""

from __future__ import annotations

import sys

import boto3

from s3_search.exceptions import S3PathNotFoundError
from s3_search.models import S3FileInfo

# Exact keyword-to-pattern mapping for file type filtering.
FILE_TYPE_PATTERNS: dict[str, str] = {
    "fintrans": "fintrans_",
    "fintrans_ira": "fintrans_ira_",
    "ordertrans": "ordertrans_",
    "accounts_add": "accounts_add_",
    "accounts_change": "accounts_change_",
    "allocation": "Allocation_",
}

VALID_FILE_TYPES: set[str] = set(FILE_TYPE_PATTERNS.keys()) | {"all"}

# Extensions to skip (compressed files).
COMPRESSED_EXTENSIONS = (".gz", ".zip", ".bz2", ".xz", ".zst")


def discover_files(
    session: boto3.Session,
    bucket: str,
    date: str,
    file_types: list[str],
) -> list[S3FileInfo]:
    """List and filter S3 files under the ICLEAR_S3 path for the given date.

    Args:
        session: Authenticated boto3 session.
        bucket: S3 bucket name.
        date: Date string in YYYYMMDD format.
        file_types: List of file type keywords to filter, or ['all'].

    Returns:
        List of S3FileInfo objects for files to search.

    Raises:
        S3PathNotFoundError: If no files are found at the path.
    """
    s3 = session.client("s3")
    prefix = f"{date}/ICLEAR_S3/"
    all_files: list[S3FileInfo] = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if "Contents" not in page:
            continue
        for obj in page["Contents"]:
            key: str = obj["Key"]
            filename = key.rsplit("/", 1)[-1]
            if not filename:
                continue  # skip directory markers
            if any(filename.endswith(ext) for ext in COMPRESSED_EXTENSIONS):
                continue  # skip compressed files
            all_files.append(
                S3FileInfo(key=key, filename=filename, size=obj["Size"])
            )

    if not all_files:
        raise S3PathNotFoundError(bucket=bucket, date=date)

    # Apply file-type filter
    if file_types != ["all"]:
        filtered = _filter_by_file_type(all_files, file_types)
        if not filtered:
            types_str = ", ".join(file_types)
            print(
                f"No files matching type '{types_str}' found",
                file=sys.stderr,
            )
            return []
        all_files = filtered

    print(f"Found {len(all_files)} files to search", file=sys.stderr)
    return all_files


def _filter_by_file_type(
    files: list[S3FileInfo],
    file_types: list[str],
) -> list[S3FileInfo]:
    """Filter files by exact file type keyword match.

    Special case: 'fintrans' matches files containing 'fintrans_' but NOT
    files containing 'fintrans_ira_'.
    """
    result: list[S3FileInfo] = []
    for file_info in files:
        for ft in file_types:
            pattern = FILE_TYPE_PATTERNS[ft]
            if pattern in file_info.filename:
                # Disambiguation: 'fintrans' should not match 'fintrans_ira'
                if ft == "fintrans" and "fintrans_ira" in file_info.filename:
                    continue
                result.append(file_info)
                break  # avoid duplicates if file matches multiple types
    return result
