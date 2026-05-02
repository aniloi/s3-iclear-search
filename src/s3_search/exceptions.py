"""Custom exceptions for the S3 ICLEAR Fintrans Search Tool."""


class AuthenticationError(Exception):
    """Raised when STS get_caller_identity fails."""

    def __init__(self, profile: str, message: str) -> None:
        self.profile = profile
        super().__init__(message)


class AmbiguousProfileError(Exception):
    """Raised when a profile name matches multiple environment keywords."""

    def __init__(self, profile: str, matching_keywords: list[str]) -> None:
        self.profile = profile
        self.matching_keywords = matching_keywords
        keywords_str = ", ".join(matching_keywords)
        super().__init__(
            f"Profile '{profile}' matches multiple environments: {keywords_str}. "
            f"Use --bucket to specify the bucket explicitly."
        )


class S3PathNotFoundError(Exception):
    """Raised when the ICLEAR_S3 path doesn't exist or is empty."""

    def __init__(self, bucket: str, date: str) -> None:
        self.bucket = bucket
        self.date = date
        super().__init__(f"No ICLEAR_S3 folder found for date {date}")


class FileStreamError(Exception):
    """Raised on S3 streaming failure (used internally for retry logic)."""

    def __init__(self, filename: str, attempt: int, cause: str) -> None:
        self.filename = filename
        self.attempt = attempt
        self.cause = cause
        super().__init__(f"Failed to stream {filename} (attempt {attempt}): {cause}")
