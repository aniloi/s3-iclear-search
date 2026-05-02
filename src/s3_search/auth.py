"""AWS authentication validation."""

from __future__ import annotations

import sys

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    ProfileNotFound,
)

from s3_search.exceptions import AuthenticationError


def validate_auth(profile: str) -> boto3.Session:
    """Validate AWS credentials for the given profile.

    Creates a boto3 session and calls STS get_caller_identity to verify
    the credentials are valid and not expired.

    Args:
        profile: AWS CLI profile name.

    Returns:
        An authenticated boto3 Session.

    Raises:
        AuthenticationError: If authentication fails for any reason.
    """
    try:
        session = boto3.Session(profile_name=profile)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        arn = identity.get("Arn", "unknown")
        print(f"Authenticated as {arn}", file=sys.stderr)
        return session
    except ProfileNotFound:
        raise AuthenticationError(
            profile=profile,
            message=(
                f"AWS profile '{profile}' not found. "
                f"Check your AWS configuration."
            ),
        )
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        raise AuthenticationError(
            profile=profile,
            message=(
                f"Authentication failed for profile '{profile}'. "
                f"Run: aws sso login --profile {profile}\n"
                f"Error: {exc}"
            ),
        )
