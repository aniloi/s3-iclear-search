"""Environment-aware bucket resolution from AWS profile names."""

from __future__ import annotations

from s3_search.exceptions import AmbiguousProfileError

PROFILE_BUCKET_MAP: dict[str, str] = {
    "dev": "dev.drivewealth.aod",
    "qa": "qa.drivewealth.aod",
    "uat": "uat.drivewealth.aod",
    "prod": "prod.drivewealth.aod",
}

FALLBACK_BUCKET = "qa.drivewealth.aod"


def resolve_bucket(profile: str, explicit_bucket: str | None = None) -> str:
    """Resolve the S3 bucket name from the profile or explicit override.

    Args:
        profile: AWS profile name.
        explicit_bucket: Explicit bucket override from --bucket flag.

    Returns:
        The resolved bucket name.

    Raises:
        AmbiguousProfileError: If the profile matches multiple environment keywords.
    """
    if explicit_bucket:
        return explicit_bucket

    profile_lower = profile.lower()
    matching_keywords = [
        keyword
        for keyword in PROFILE_BUCKET_MAP
        if keyword in profile_lower
    ]

    if len(matching_keywords) == 1:
        return PROFILE_BUCKET_MAP[matching_keywords[0]]

    if len(matching_keywords) == 0:
        return FALLBACK_BUCKET

    # Multiple matches — ambiguous profile
    raise AmbiguousProfileError(profile=profile, matching_keywords=matching_keywords)
