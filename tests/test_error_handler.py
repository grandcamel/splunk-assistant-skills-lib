"""Tests for error_handler module."""

import pytest

from splunk_assistant_skills_lib.error_handler import (
    AuthenticationError,
    AuthorizationError,
    JobFailedError,
    NotFoundError,
    RateLimitError,
    SearchQuotaError,
    ServerError,
    SplunkError,
    ValidationError,
    format_error_for_json,
    parse_error_response,
    sanitize_error_message,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_splunk_error_is_base(self):
        """Test SplunkError is the base exception."""
        assert issubclass(AuthenticationError, SplunkError)
        assert issubclass(AuthorizationError, SplunkError)
        assert issubclass(ValidationError, SplunkError)
        assert issubclass(NotFoundError, SplunkError)
        assert issubclass(RateLimitError, SplunkError)
        assert issubclass(SearchQuotaError, SplunkError)
        assert issubclass(JobFailedError, SplunkError)
        assert issubclass(ServerError, SplunkError)

    def test_all_inherit_from_exception(self):
        """Test all errors inherit from Exception."""
        assert issubclass(SplunkError, Exception)


class TestSplunkError:
    """Tests for SplunkError base class."""

    def test_message_only(self):
        """Test error with message only."""
        error = SplunkError("Test error")
        assert str(error) == "Test error"

    def test_with_operation(self):
        """Test error with operation context."""
        error = SplunkError("Test error", operation="search")
        assert "search" in str(error) or error.operation == "search"

    def test_with_details(self):
        """Test error with details."""
        error = SplunkError("Test error", details={"key": "value"})
        assert error.details == {"key": "value"}


class TestValidationError:
    """Tests for ValidationError."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        error = ValidationError("Invalid input")
        assert "Invalid input" in str(error)

    def test_with_field_details(self):
        """Test validation error with field details."""
        error = ValidationError("Invalid", details={"field": "username"})
        assert error.details["field"] == "username"


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_authentication_error(self):
        """Test authentication error."""
        error = AuthenticationError("Invalid credentials")
        assert "Invalid credentials" in str(error)


class TestAuthorizationError:
    """Tests for AuthorizationError."""

    def test_authorization_error(self):
        """Test authorization error."""
        error = AuthorizationError("Access denied")
        assert "Access denied" in str(error)


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_not_found_error(self):
        """Test not found error."""
        error = NotFoundError("Resource not found")
        assert "not found" in str(error).lower()


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError("Too many requests")
        assert "Too many requests" in str(error)


class TestSearchQuotaError:
    """Tests for SearchQuotaError."""

    def test_search_quota_error(self):
        """Test search quota error."""
        error = SearchQuotaError("Quota exceeded")
        assert "Quota exceeded" in str(error)


class TestJobFailedError:
    """Tests for JobFailedError."""

    def test_job_failed_error(self):
        """Test job failed error."""
        error = JobFailedError("Job failed", details={"sid": "123.456"})
        assert "Job failed" in str(error)
        assert error.details["sid"] == "123.456"


class TestServerError:
    """Tests for ServerError."""

    def test_server_error(self):
        """Test server error."""
        error = ServerError("Internal server error")
        assert "Internal server error" in str(error)


class TestSanitizeErrorMessage:
    """Tests for sanitize_error_message function."""

    def test_removes_credentials(self):
        """Test that credentials are removed from messages."""
        message = "Error connecting to https://user:password@splunk.example.com"
        result = sanitize_error_message(message)
        assert "password" not in result

    def test_preserves_safe_content(self):
        """Test that safe content is preserved."""
        message = "Search failed: index not found"
        result = sanitize_error_message(message)
        assert "Search failed" in result


class TestParseErrorResponse:
    """Tests for parse_error_response function."""

    def test_parses_messages_list(self):
        """Test parsing response with messages list."""
        from unittest.mock import MagicMock

        response = MagicMock()
        response.json.return_value = {
            "messages": [{"text": "Error occurred", "type": "ERROR"}]
        }
        result = parse_error_response(response)
        assert "Error occurred" in str(result)

    def test_parses_message_field(self):
        """Test parsing response with message field."""
        from unittest.mock import MagicMock

        response = MagicMock()
        response.json.return_value = {"message": "Something went wrong"}
        result = parse_error_response(response)
        assert "Something went wrong" in str(result)

    def test_handles_json_decode_error(self):
        """Test handling JSON decode error."""
        import json
        from unittest.mock import MagicMock

        response = MagicMock()
        response.json.side_effect = json.JSONDecodeError("test", "doc", 0)
        response.text = "Raw error text"
        result = parse_error_response(response)
        assert result is not None


class TestFormatErrorForJson:
    """Tests for format_error_for_json function."""

    def test_formats_splunk_error(self):
        """Test formatting SplunkError for JSON."""
        error = SplunkError("Test error", operation="search")
        result = format_error_for_json(error)
        assert "error" in result or "message" in result
        assert isinstance(result, dict)

    def test_formats_validation_error(self):
        """Test formatting ValidationError for JSON."""
        error = ValidationError("Invalid input", details={"field": "query"})
        result = format_error_for_json(error)
        assert isinstance(result, dict)
