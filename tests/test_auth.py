"""Tests for AWS authentication validation."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

from s3_search.auth import validate_auth
from s3_search.exceptions import AuthenticationError


@patch("s3_search.auth.boto3.Session")
def test_successful_auth(mock_session_cls):
    mock_session = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.return_value = {
        "Arn": "arn:aws:iam::123456:user/testuser"
    }
    mock_session.client.return_value = mock_sts
    mock_session_cls.return_value = mock_session

    session = validate_auth("qa")
    assert session is mock_session
    mock_session_cls.assert_called_once_with(profile_name="qa")


@patch("s3_search.auth.boto3.Session")
def test_profile_not_found(mock_session_cls):
    mock_session_cls.side_effect = ProfileNotFound(profile="nonexistent")
    with pytest.raises(AuthenticationError, match="not found"):
        validate_auth("nonexistent")


@patch("s3_search.auth.boto3.Session")
def test_expired_credentials(mock_session_cls):
    mock_session = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.side_effect = ClientError(
        {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
        "GetCallerIdentity",
    )
    mock_session.client.return_value = mock_sts
    mock_session_cls.return_value = mock_session

    with pytest.raises(AuthenticationError, match="aws sso login"):
        validate_auth("qa")
