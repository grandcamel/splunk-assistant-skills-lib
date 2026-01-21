"""Tests for formatters module."""

import pytest

from splunk_as.formatters import (
    Colors,
    SENSITIVE_FIELD_PATTERNS,
    _is_sensitive_field,
    _redact_sensitive_value,
    colorize,
    format_duration,
    format_job_status,
    format_json,
    format_list,
    format_metadata,
    format_saved_search,
    format_search_results,
    format_splunk_time,
    format_table,
    supports_color,
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

    def test_with_different_colors(self):
        """Test colorize with different color strings."""
        for color in ["red", "green", "blue", "yellow", "cyan", "magenta"]:
            result = colorize("test", color)
            assert "test" in result


class TestSupportsColor:
    """Tests for supports_color function."""

    def test_returns_bool(self):
        """Test supports_color returns boolean."""
        result = supports_color()
        assert isinstance(result, bool)


class TestSensitiveFieldPatterns:
    """Tests for SENSITIVE_FIELD_PATTERNS constant."""

    def test_is_frozenset(self):
        """Test SENSITIVE_FIELD_PATTERNS is a frozenset."""
        assert isinstance(SENSITIVE_FIELD_PATTERNS, frozenset)

    def test_contains_expected_patterns(self):
        """Test all expected patterns are present."""
        expected = {
            "password",
            "passwd",
            "token",
            "api_key",
            "apikey",
            "secret",
            "auth",
            "authorization",
            "credential",
            "private_key",
            "privatekey",
            "access_token",
            "refresh_token",
            "session_key",
            "sessionkey",
            "splunk_token",
            "bearer",
        }
        assert expected == SENSITIVE_FIELD_PATTERNS


class TestFormatSearchResultsExtended:
    """Extended tests for format_search_results function."""

    def test_dict_with_results_key(self):
        """Test dict input with 'results' key."""
        data = {"results": [{"host": "server1", "count": "100"}]}
        output = format_search_results(data)
        assert "server1" in output
        assert "100" in output

    def test_dict_with_rows_key(self):
        """Test dict input with 'rows' key."""
        data = {"rows": [{"host": "server1", "count": "100"}]}
        output = format_search_results(data)
        assert "server1" in output

    def test_dict_with_entry_key(self):
        """Test dict input with 'entry' key (REST API format)."""
        data = {
            "entry": [
                {"content": {"host": "server1", "count": "100"}},
                {"content": {"host": "server2", "count": "200"}},
            ]
        }
        output = format_search_results(data)
        assert "server1" in output
        assert "server2" in output

    def test_empty_results(self):
        """Test empty results returns no results message."""
        output = format_search_results([])
        assert "No results found" in output

    def test_empty_dict_results(self):
        """Test empty dict results."""
        output = format_search_results({"results": []})
        assert "No results found" in output

    def test_max_results_truncation(self):
        """Test results are truncated at max_results."""
        results = [{"index": i} for i in range(100)]
        output = format_search_results(results, max_results=10)
        assert "showing first 10" in output

    def test_max_results_no_truncation(self):
        """Test no truncation message when under max."""
        results = [{"index": i} for i in range(5)]
        output = format_search_results(results, max_results=10)
        assert "showing first" not in output

    def test_output_format_json(self):
        """Test JSON output format."""
        results = [{"host": "server1"}]
        output = format_search_results(results, output_format="json")
        assert '"host"' in output
        assert '"server1"' in output

    def test_output_format_csv(self):
        """Test CSV output format."""
        results = [{"host": "server1", "count": "100"}]
        output = format_search_results(results, fields=["host", "count"], output_format="csv")
        assert "host" in output
        assert "server1" in output

    def test_output_format_table_default(self):
        """Test table is default output format."""
        results = [{"host": "server1"}]
        output = format_search_results(results, output_format="table")
        assert "server1" in output

    def test_fields_parameter(self):
        """Test fields parameter limits columns."""
        results = [{"host": "server1", "count": "100", "extra": "data"}]
        output = format_search_results(results, fields=["host"])
        assert "server1" in output

    def test_excludes_internal_fields_by_default(self):
        """Test internal fields (starting with _) are excluded by default."""
        results = [{"host": "server1", "_raw": "raw data", "_time": "123"}]
        # Table format auto-selects non-internal fields
        output = format_search_results(results)
        assert "server1" in output

    def test_multiple_sensitive_fields_redacted(self):
        """Test multiple sensitive fields are all redacted."""
        results = [
            {
                "host": "server1",
                "password": "secret1",
                "api_key": "key123",
                "token": "tok456",
            }
        ]
        output = format_search_results(results)
        assert "server1" in output
        assert "secret1" not in output
        assert "key123" not in output
        assert "tok456" not in output


class TestFormatJobStatus:
    """Tests for format_job_status function."""

    def test_basic_job_status(self):
        """Test basic job status formatting."""
        job = {
            "content": {
                "sid": "1234567890.12345",
                "dispatchState": "DONE",
                "doneProgress": 1.0,
                "eventCount": 1000,
                "resultCount": 500,
                "scanCount": 10000,
                "runDuration": 5.25,
            }
        }
        output = format_job_status(job)
        assert "1234567890.12345" in output
        assert "DONE" in output
        assert "100.0%" in output
        assert "1,000" in output
        assert "500" in output
        assert "10,000" in output
        assert "5.25s" in output

    def test_job_without_content_wrapper(self):
        """Test job status without content wrapper."""
        job = {
            "sid": "1234567890.12345",
            "dispatchState": "RUNNING",
            "doneProgress": 0.5,
            "eventCount": 500,
            "resultCount": 250,
            "scanCount": 5000,
            "runDuration": 2.5,
        }
        output = format_job_status(job)
        assert "1234567890.12345" in output
        assert "RUNNING" in output
        assert "50.0%" in output

    def test_job_states(self):
        """Test different job states are formatted."""
        states = ["QUEUED", "PARSING", "RUNNING", "FINALIZING", "DONE", "FAILED", "PAUSED"]
        for state in states:
            job = {"content": {"sid": "test", "dispatchState": state, "doneProgress": 0}}
            output = format_job_status(job)
            assert state in output

    def test_failed_job_with_error_message(self):
        """Test failed job includes error message."""
        job = {
            "content": {
                "sid": "test",
                "dispatchState": "FAILED",
                "doneProgress": 0,
                "messages": [{"text": "Search syntax error"}],
            }
        }
        output = format_job_status(job)
        assert "FAILED" in output
        assert "Error:" in output
        assert "Search syntax error" in output

    def test_unknown_state(self):
        """Test unknown state is handled."""
        job = {"content": {"sid": "test", "dispatchState": "UNKNOWN_STATE", "doneProgress": 0}}
        output = format_job_status(job)
        assert "UNKNOWN_STATE" in output

    def test_missing_sid(self):
        """Test missing SID shows Unknown."""
        job = {"content": {"dispatchState": "DONE", "doneProgress": 1.0}}
        output = format_job_status(job)
        assert "Unknown" in output

    def test_zero_values(self):
        """Test zero values are handled."""
        job = {
            "content": {
                "sid": "test",
                "dispatchState": "QUEUED",
                "doneProgress": 0,
                "eventCount": 0,
                "resultCount": 0,
                "scanCount": 0,
                "runDuration": 0,
            }
        }
        output = format_job_status(job)
        assert "0.0%" in output
        assert "0.00s" in output


class TestFormatMetadata:
    """Tests for format_metadata function."""

    def test_index_metadata(self):
        """Test index metadata formatting."""
        meta = {
            "title": "main",
            "totalEventCount": 1000000,
            "currentDBSizeMB": 512,
            "minTime": "2024-01-01T00:00:00.000-05:00",
            "maxTime": "2024-01-15T23:59:59.000-05:00",
        }
        output = format_metadata(meta)
        assert "Index:" in output
        assert "main" in output
        assert "Total Events:" in output
        assert "1,000,000" in output
        assert "Total Size:" in output
        assert "Earliest Event:" in output
        assert "Latest Event:" in output

    def test_index_metadata_with_name_fallback(self):
        """Test index metadata uses name when title missing."""
        meta = {
            "name": "internal",
            "totalEventCount": 500,
            "currentDBSizeMB": 10,
        }
        output = format_metadata(meta)
        assert "internal" in output

    def test_field_values_metadata(self):
        """Test field values metadata formatting."""
        meta = {
            "field": "status",
            "values": [
                {"value": "200", "count": 1000},
                {"value": "404", "count": 50},
                {"value": "500", "count": 10},
            ],
        }
        output = format_metadata(meta)
        assert "Field:" in output
        assert "status" in output
        assert "Values:" in output
        assert "200" in output
        assert "1,000" in output
        assert "404" in output
        assert "500" in output

    def test_field_values_truncated_to_10(self):
        """Test field values are limited to first 10."""
        meta = {
            "field": "host",
            "values": [{"value": f"host{i}", "count": i} for i in range(20)],
        }
        output = format_metadata(meta)
        assert "host9" in output  # Last in first 10
        assert "host10" not in output  # 11th value

    def test_generic_metadata(self):
        """Test generic metadata formatting."""
        meta = {"name": "test", "count": 100, "enabled": True}
        output = format_metadata(meta)
        assert "name: test" in output
        assert "count: 100" in output
        assert "enabled: True" in output

    def test_excludes_internal_fields(self):
        """Test internal fields starting with _ are excluded."""
        meta = {"name": "test", "_raw": "raw data", "_time": "123"}
        output = format_metadata(meta)
        assert "name: test" in output
        assert "_raw" not in output
        assert "_time" not in output

    def test_redacts_sensitive_fields(self):
        """Test sensitive fields are redacted in generic metadata."""
        meta = {"name": "test", "password": "secret123", "api_key": "key456"}
        output = format_metadata(meta)
        assert "name: test" in output
        assert "secret123" not in output
        assert "key456" not in output
        assert "[REDACTED]" in output


class TestFormatSavedSearch:
    """Tests for format_saved_search function."""

    def test_basic_saved_search(self):
        """Test basic saved search formatting."""
        search = {
            "name": "My Saved Search",
            "content": {
                "eai:acl": {"app": "search", "owner": "admin"},
                "search": "index=main | stats count",
                "disabled": False,
                "is_scheduled": False,
            },
        }
        output = format_saved_search(search)
        assert "Name:" in output
        assert "My Saved Search" in output
        assert "App:" in output
        assert "search" in output
        assert "Owner:" in output
        assert "admin" in output
        assert "Search:" in output
        assert "stats count" in output
        assert "Disabled:" in output
        assert "Scheduled:" in output

    def test_scheduled_saved_search(self):
        """Test scheduled saved search includes cron info."""
        search = {
            "name": "Scheduled Report",
            "content": {
                "eai:acl": {"app": "search", "owner": "admin"},
                "search": "index=main | stats count",
                "disabled": False,
                "is_scheduled": True,
                "cron_schedule": "0 6 * * *",
                "next_scheduled_time": "2024-01-16T06:00:00.000-05:00",
            },
        }
        output = format_saved_search(search)
        assert "Scheduled:" in output
        assert "True" in output
        assert "Cron:" in output
        assert "0 6 * * *" in output
        assert "Next Run:" in output

    def test_search_without_content_wrapper(self):
        """Test saved search without content wrapper."""
        search = {
            "name": "Direct Search",
            "eai:acl": {"app": "myapp", "owner": "user1"},
            "search": "index=web | head 100",
            "disabled": True,
            "is_scheduled": False,
        }
        output = format_saved_search(search)
        assert "Direct Search" in output
        assert "myapp" in output
        assert "user1" in output
        assert "True" in output  # disabled

    def test_long_search_truncated(self):
        """Test long search query is truncated."""
        long_search = "index=main " + "| stats count by field " * 20
        search = {
            "content": {
                "name": "Long Search",
                "search": long_search,
                "disabled": False,
                "is_scheduled": False,
            }
        }
        output = format_saved_search(search)
        assert "..." in output  # Truncation indicator


class TestFormatSplunkTime:
    """Tests for format_splunk_time function."""

    def test_iso_format(self):
        """Test ISO format timestamp."""
        result = format_splunk_time("2024-01-15T10:30:45.000-05:00")
        assert "2024-01-15" in result

    def test_empty_string(self):
        """Test empty string returns empty or formatted."""
        result = format_splunk_time("")
        assert isinstance(result, str)

    def test_unix_timestamp(self):
        """Test unix timestamp string."""
        result = format_splunk_time("1705329045")
        assert isinstance(result, str)


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_milliseconds(self):
        """Test duration under 1 second shows milliseconds."""
        assert format_duration(0.5) == "500ms"
        assert format_duration(0.001) == "1ms"
        assert format_duration(0.999) == "999ms"

    def test_seconds(self):
        """Test duration under 1 minute shows seconds."""
        assert format_duration(1.0) == "1.0s"
        assert format_duration(30.5) == "30.5s"
        assert format_duration(59.9) == "59.9s"

    def test_minutes(self):
        """Test duration under 1 hour shows minutes."""
        assert format_duration(60) == "1.0m"
        assert format_duration(90) == "1.5m"
        assert format_duration(3599) == "60.0m"

    def test_hours(self):
        """Test duration 1 hour or more shows hours."""
        assert format_duration(3600) == "1.0h"
        assert format_duration(5400) == "1.5h"
        assert format_duration(7200) == "2.0h"
        assert format_duration(36000) == "10.0h"

    def test_boundary_values(self):
        """Test boundary values between units."""
        # Just under 1 second
        assert "ms" in format_duration(0.9999)
        # Exactly 1 second
        assert "s" in format_duration(1.0)
        # Just under 1 minute
        assert "s" in format_duration(59.999)
        # Exactly 1 minute
        assert "m" in format_duration(60)
        # Just under 1 hour
        assert "m" in format_duration(3599)
        # Exactly 1 hour
        assert "h" in format_duration(3600)


class TestColorsClass:
    """Tests for Colors class constants."""

    def test_colors_are_strings(self):
        """Test color constants are strings."""
        assert isinstance(Colors.RED, str)
        assert isinstance(Colors.GREEN, str)
        assert isinstance(Colors.BLUE, str)
        assert isinstance(Colors.YELLOW, str)
        assert isinstance(Colors.CYAN, str)
        assert isinstance(Colors.MAGENTA, str)
        assert isinstance(Colors.RESET, str)

    def test_reset_is_defined(self):
        """Test RESET color is defined for ending color sequences."""
        assert Colors.RESET is not None
