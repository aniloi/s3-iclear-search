"""Tests for environment-aware bucket resolution."""

import pytest

from s3_search.bucket_resolver import FALLBACK_BUCKET, resolve_bucket
from s3_search.exceptions import AmbiguousProfileError


def test_explicit_bucket_overrides():
    result = resolve_bucket("qa", explicit_bucket="custom.bucket")
    assert result == "custom.bucket"


def test_qa_profile():
    assert resolve_bucket("qa") == "qa.drivewealth.aod"


def test_dev_profile():
    assert resolve_bucket("dev") == "dev.drivewealth.aod"


def test_uat_profile():
    assert resolve_bucket("uat") == "uat.drivewealth.aod"


def test_prod_profile():
    assert resolve_bucket("prod") == "prod.drivewealth.aod"


def test_profile_with_keyword_substring():
    assert resolve_bucket("my-qa-profile") == "qa.drivewealth.aod"


def test_profile_case_insensitive():
    assert resolve_bucket("QA-Team") == "qa.drivewealth.aod"


def test_unknown_profile_uses_fallback():
    assert resolve_bucket("staging") == FALLBACK_BUCKET


def test_ambiguous_profile_raises():
    with pytest.raises(AmbiguousProfileError) as exc_info:
        resolve_bucket("qa-prod-migration")
    assert "qa" in exc_info.value.matching_keywords
    assert "prod" in exc_info.value.matching_keywords


def test_ambiguous_profile_message_suggests_bucket():
    with pytest.raises(AmbiguousProfileError, match="--bucket"):
        resolve_bucket("dev-qa-sync")
