"""Tests for dynamic AWS profile detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from s3_search.api.profiles import (
    _parse_aws_config,
    _parse_aws_credentials,
    detect_profiles,
)


@pytest.fixture
def aws_config_file(tmp_path: Path) -> Path:
    """Create a mock ~/.aws/config file."""
    config = tmp_path / "config"
    config.write_text(
        "[default]\nregion = us-east-1\n\n"
        "[profile qa]\nregion = us-east-1\n\n"
        "[profile uat]\nregion = us-east-1\n\n"
        "[profile prod]\nregion = us-east-1\n\n"
        "[profile custom-team]\nregion = us-west-2\n"
    )
    return config


@pytest.fixture
def aws_credentials_file(tmp_path: Path) -> Path:
    """Create a mock ~/.aws/credentials file."""
    creds = tmp_path / "credentials"
    creds.write_text(
        "[default]\naws_access_key_id = AKIA...\n\n"
        "[dev]\naws_access_key_id = AKIA...\n"
    )
    return creds


class TestParseAwsConfig:
    """Tests for _parse_aws_config."""

    def test_parses_profiles(self, aws_config_file: Path):
        profiles = _parse_aws_config(aws_config_file)
        assert "default" in profiles
        assert "qa" in profiles
        assert "uat" in profiles
        assert "prod" in profiles
        assert "custom-team" in profiles

    def test_missing_file_returns_empty(self, tmp_path: Path):
        profiles = _parse_aws_config(tmp_path / "nonexistent")
        assert profiles == []

    def test_empty_file(self, tmp_path: Path):
        empty = tmp_path / "config"
        empty.write_text("")
        profiles = _parse_aws_config(empty)
        assert profiles == []


class TestParseAwsCredentials:
    """Tests for _parse_aws_credentials."""

    def test_parses_sections(self, aws_credentials_file: Path):
        profiles = _parse_aws_credentials(aws_credentials_file)
        assert "default" in profiles
        assert "dev" in profiles

    def test_missing_file_returns_empty(self, tmp_path: Path):
        profiles = _parse_aws_credentials(tmp_path / "nonexistent")
        assert profiles == []


class TestDetectProfiles:
    """Tests for detect_profiles with mocked AWS directory."""

    def test_detect_profiles_sorted(self, tmp_path: Path, aws_config_file: Path, aws_credentials_file: Path):
        aws_dir = tmp_path
        with patch("s3_search.api.profiles.Path.home", return_value=tmp_path):
            # Create .aws directory structure
            aws_path = tmp_path / ".aws"
            aws_path.mkdir()
            (aws_path / "config").write_text(aws_config_file.read_text())
            (aws_path / "credentials").write_text(aws_credentials_file.read_text())

            profiles = detect_profiles()

        names = [p.name for p in profiles]
        # Known environments should come first
        known_names = [n for n in names if any(env in n.lower() for env in ("dev", "qa", "uat", "prod"))]
        other_names = [n for n in names if n not in known_names]
        assert len(known_names) > 0
        # Known should appear before others
        if other_names:
            first_other_idx = names.index(other_names[0])
            last_known_idx = names.index(known_names[-1])
            assert last_known_idx < first_other_idx

    def test_detect_profiles_no_aws_dir(self, tmp_path: Path):
        with patch("s3_search.api.profiles.Path.home", return_value=tmp_path):
            profiles = detect_profiles()
        assert profiles == []

    def test_known_profiles_have_buckets(self, tmp_path: Path):
        aws_path = tmp_path / ".aws"
        aws_path.mkdir()
        (aws_path / "config").write_text("[profile qa]\nregion = us-east-1\n")

        with patch("s3_search.api.profiles.Path.home", return_value=tmp_path):
            profiles = detect_profiles()

        qa_profiles = [p for p in profiles if p.name == "qa"]
        assert len(qa_profiles) == 1
        assert qa_profiles[0].resolved_bucket == "qa.drivewealth.aod"
        assert qa_profiles[0].is_known is True
