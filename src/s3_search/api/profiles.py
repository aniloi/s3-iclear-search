"""Dynamic AWS profile detection from ~/.aws configuration files."""

from __future__ import annotations

import configparser
import os
from pathlib import Path

from s3_search.api.models import ProfileInfo
from s3_search.bucket_resolver import resolve_bucket
from s3_search.exceptions import AmbiguousProfileError

# Known environment keywords in priority order for sorting.
_KNOWN_ENVS = ("dev", "qa", "uat", "prod")


def _parse_aws_config(path: Path) -> list[str]:
    """Parse profile names from an AWS config file.

    Config files use ``[profile X]`` sections (except ``[default]``).
    """
    if not path.is_file():
        return []
    parser = configparser.ConfigParser()
    try:
        parser.read(str(path), encoding="utf-8")
    except (configparser.Error, OSError):
        return []

    profiles: list[str] = []
    for section in parser.sections():
        if section == "default":
            profiles.append("default")
        elif section.startswith("profile "):
            name = section[len("profile ") :].strip()
            if name:
                profiles.append(name)
    return profiles


def _parse_aws_credentials(path: Path) -> list[str]:
    """Parse profile names from an AWS credentials file.

    Credentials files use plain ``[X]`` sections.
    """
    if not path.is_file():
        return []
    parser = configparser.ConfigParser()
    try:
        parser.read(str(path), encoding="utf-8")
    except (configparser.Error, OSError):
        return []

    return [s for s in parser.sections() if s]


def _sort_key(profile: ProfileInfo) -> tuple[int, str]:
    """Sort known environments first (in _KNOWN_ENVS order), then alphabetical."""
    name_lower = profile.name.lower()
    for idx, env in enumerate(_KNOWN_ENVS):
        if env in name_lower:
            return (0, f"{idx:04d}_{profile.name}")
    return (1, profile.name)


def detect_profiles() -> list[ProfileInfo]:
    """Detect available AWS profiles and resolve their buckets.

    Reads ``~/.aws/config`` and ``~/.aws/credentials`` to discover
    profile names, then attempts bucket resolution for each.

    Returns:
        Sorted list of ProfileInfo (known environments first, then alphabetical).
    """
    aws_dir = Path.home() / ".aws"
    config_profiles = _parse_aws_config(aws_dir / "config")
    creds_profiles = _parse_aws_credentials(aws_dir / "credentials")

    # Union of both sources, preserving order (config first).
    seen: set[str] = set()
    all_names: list[str] = []
    for name in config_profiles + creds_profiles:
        if name not in seen:
            seen.add(name)
            all_names.append(name)

    result: list[ProfileInfo] = []
    for name in all_names:
        try:
            bucket = resolve_bucket(name, None)
            # If resolve_bucket returns the fallback, the profile is not "known".
            is_known = any(env in name.lower() for env in _KNOWN_ENVS)
            result.append(ProfileInfo(name=name, resolved_bucket=bucket, is_known=is_known))
        except AmbiguousProfileError:
            result.append(ProfileInfo(name=name, resolved_bucket=None, is_known=False))

    result.sort(key=_sort_key)
    return result
