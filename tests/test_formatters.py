"""Tests for formatters module."""

import pytest

from splunk_assistant_skills_lib.formatters import (
    SENSITIVE_FIELD_PATTERNS,
    _is_sensitive_field,
    _redact_sensitive_value,
    colorize,
    format_json,
    format_list,
    format_search_results,
    format_table,
)


class TestSensitiveFieldDetection:
    """Tests for sensitive field detection and redaction."""

    def test_password_detected(self):
        """Test password field is detected."""
        assert _is_sensitive_field("password")
        assert _is_sensitive_field("PASSWORD")
        assert _is_sensitive_field("user_password")
        assert _is_sensitive_field("password_hash")

    def test_token_detected(self):
        """Test token field is detected."""
        assert _is_sensitive_field("token")
        assert _is_sensitive_field("api_token")
        assert _is_sensitive_field("access_token")
        assert _is_sensitive_field("refresh_token")

    def test_secret_detected(self):
        """Test secret field is detected."""
        assert _is_sensitive_field("secret")
        assert _is_sensitive_field("client_secret")
        assert _is_sensitive_field("secret_key")

    def test_api_key_detected(self):
        """Test api_key field is detected."""
        assert _is_sensitive_field("api_key")
        assert _is_sensitive_field("apikey")
        assert _is_sensitive_field("x_api_key")

    def test_credential_detected(self):
        """Test credential field is detected."""
        assert _is_sensitive_field("credential")
        assert _is_sensitive_field("credentials")
        assert _is_sensitive_field("user_credentials")

    def test_auth_detected(self):
        """Test auth field is detected."""
        assert _is_sensitive_field("auth")
        assert _is_sensitive_field("authorization")
        assert _is_sensitive_field("auth_header")

    def test_private_key_detected(self):
        """Test private_key field is detected."""
        assert _is_sensitive_field("private_key")
        assert _is_sensitive_field("privatekey")

    def test_session_key_detected(self):
        """Test session_key field is detected."""
        assert _is_sensitive_field("session_key")
        assert _is_sensitive_field("sessionkey")

    def test_bearer_detected(self):
        """Test bearer field is detected."""
        assert _is_sensitive_field("bearer")
        assert _is_sensitive_field("bearer_token")

    def test_non_sensitive_not_detected(self):
        """Test non-sensitive fields are not flagged."""
        assert not _is_sensitive_field("host")
        assert not _is_sensitive_field("username")
        assert not _is_sensitive_field("email")
        assert not _is_sensitive_field("count")
        assert not _is_sensitive_field("status")


class TestRedactSensitiveValue:
    """Tests for _redact_sensitive_value function."""

    def test_redacts_sensitive_field(self):
        """Test sensitive field value is redacted."""
        assert _redact_sensitive_value("password", "secret123") == "[REDACTED]"
        assert _redact_sensitive_value("api_key", "abc123") == "[REDACTED]"

    def test_preserves_non_sensitive_field(self):
        """Test non-sensitive field value is preserved."""
        assert _redact_sensitive_value("host", "server1") == "server1"
        assert _redact_sensitive_value("count", 42) == 42


class TestFormatJson:
    """Tests for format_json function."""

    def test_dict(self):
        """Test dict formatting."""
        result = format_json({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result

    def test_list(self):
        """Test list formatting."""
        result = format_json([1, 2, 3])
        assert "1" in result
        assert "2" in result
        assert "3" in result


class TestFormatTable:
    """Tests for format_table function."""

    def test_basic_table(self):
        """Test basic table formatting."""
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = format_table(data)
        assert "Alice" in result
        assert "Bob" in result
        assert "30" in result
        assert "25" in result

    def test_with_columns(self):
        """Test table with specific columns."""
        data = [{"name": "Alice", "age": 30, "city": "NYC"}]
        result = format_table(data, columns=["name", "age"])
        assert "Alice" in result
        assert "30" in result

    def test_empty_data(self):
        """Test empty data returns some output."""
        result = format_table([])
        # Just verify it doesn't crash and returns something
        assert isinstance(result, str)


class TestFormatList:
    """Tests for format_list function."""

    def test_basic_list(self):
        """Test basic list formatting."""
        result = format_list(["item1", "item2", "item3"])
        assert "item1" in result
        assert "item2" in result
        assert "item3" in result


class TestFormatSearchResults:
    """Tests for format_search_results with sensitive field redaction."""

    def test_redacts_sensitive_fields(self):
        """Test that sensitive fields are redacted in results."""
        results = [{"host": "server1", "password": "secret123"}]
        output = format_search_results(results)
        assert "server1" in output
        assert "secret123" not in output
        assert "[REDACTED]" in output

    def test_preserves_non_sensitive_fields(self):
        """Test that non-sensitive fields are preserved."""
        results = [{"host": "server1", "status": "200"}]
        output = format_search_results(results)
        assert "server1" in output
        assert "200" in output


class TestColorize:
    """Tests for colorize function."""

    def test_returns_text_when_disabled(self):
        """Test that text is returned unchanged when color disabled."""
        result = colorize("test", "green")
        # Result should contain the original text
        assert "test" in result
