"""Tests for CLI utility functions."""

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from splunk_assistant_skills_lib import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    SearchQuotaError,
    ServerError,
    SplunkError,
    ValidationError,
)
from splunk_assistant_skills_lib.cli.cli_utils import (
    MAX_JSON_SIZE,
    build_endpoint,
    extract_sid_from_response,
    get_time_bounds,
    handle_cli_errors,
    parse_comma_list,
    parse_json_arg,
    validate_non_negative_int,
    validate_positive_int,
    validate_sid_callback,
)


class TestBuildEndpoint:
    """Tests for build_endpoint function."""

    def test_no_namespace(self):
        """Test endpoint without namespace."""
        result = build_endpoint("/saved/searches")
        assert result == "/saved/searches"

    def test_with_app_only(self):
        """Test endpoint with app namespace."""
        result = build_endpoint("/saved/searches", app="search")
        assert result == "/servicesNS/-/search/saved/searches"

    def test_with_app_and_owner(self):
        """Test endpoint with app and owner namespace."""
        result = build_endpoint("/saved/searches", app="search", owner="admin")
        assert result == "/servicesNS/admin/search/saved/searches"

    def test_validates_app_path_traversal(self):
        """Test that app is validated for path traversal."""
        # ValidationError can come from either module
        with pytest.raises(Exception) as exc_info:
            build_endpoint("/saved/searches", app="../admin")
        assert "traversal" in str(exc_info.value).lower() or ".." in str(exc_info.value)

    def test_validates_owner_path_traversal(self):
        """Test that owner is validated for path traversal."""
        with pytest.raises(Exception) as exc_info:
            build_endpoint("/saved/searches", app="search", owner="../root")
        assert "traversal" in str(exc_info.value).lower() or ".." in str(exc_info.value)


class TestExtractSidFromResponse:
    """Tests for extract_sid_from_response function."""

    def test_extract_from_sid_field(self):
        """Test extraction from direct sid field (v2 API)."""
        response = {"sid": "1703779200.12345"}
        assert extract_sid_from_response(response) == "1703779200.12345"

    def test_extract_from_entry_name(self):
        """Test extraction from entry name field (v1 API)."""
        response = {"entry": [{"name": "1703779200.12345"}]}
        assert extract_sid_from_response(response) == "1703779200.12345"

    def test_extract_from_entry_content_sid(self):
        """Test extraction from entry content sid field."""
        response = {"entry": [{"content": {"sid": "1703779200.12345"}}]}
        assert extract_sid_from_response(response) == "1703779200.12345"

    def test_raises_on_missing_sid(self):
        """Test that ValueError is raised when SID cannot be extracted."""
        with pytest.raises(ValueError, match="Could not extract SID"):
            extract_sid_from_response({})

    def test_raises_on_empty_entry(self):
        """Test that ValueError is raised for empty entry list."""
        with pytest.raises(ValueError, match="Could not extract SID"):
            extract_sid_from_response({"entry": []})


class TestParseCommaList:
    """Tests for parse_comma_list function."""

    def test_simple_list(self):
        """Test parsing simple comma-separated list."""
        result = parse_comma_list("a,b,c")
        assert result == ["a", "b", "c"]

    def test_with_spaces(self):
        """Test parsing list with spaces around items."""
        result = parse_comma_list("a , b , c")
        assert result == ["a", "b", "c"]

    def test_none_input(self):
        """Test that None input returns None."""
        assert parse_comma_list(None) is None

    def test_empty_string(self):
        """Test that empty string returns None."""
        assert parse_comma_list("") is None

    def test_filters_empty_items(self):
        """Test that empty items are filtered."""
        result = parse_comma_list("a,,b,  ,c")
        assert result == ["a", "b", "c"]


class TestParseJsonArg:
    """Tests for parse_json_arg function."""

    def test_valid_json(self):
        """Test parsing valid JSON."""
        result = parse_json_arg('{"key": "value"}')
        assert result == {"key": "value"}

    def test_none_input(self):
        """Test that None input returns None."""
        assert parse_json_arg(None) is None

    def test_empty_string(self):
        """Test that empty string returns None."""
        assert parse_json_arg("") is None

    def test_invalid_json(self):
        """Test that invalid JSON raises BadParameter."""
        with pytest.raises(click.BadParameter, match="Invalid JSON"):
            parse_json_arg("not valid json")

    def test_size_limit(self):
        """Test that oversized JSON raises BadParameter."""
        large_json = '{"data": "' + "x" * (MAX_JSON_SIZE + 1) + '"}'
        with pytest.raises(click.BadParameter, match="JSON too large"):
            parse_json_arg(large_json)

    def test_custom_size_limit(self):
        """Test custom size limit."""
        with pytest.raises(click.BadParameter, match="JSON too large"):
            parse_json_arg('{"key": "value"}', max_size=5)


class TestValidatePositiveInt:
    """Tests for validate_positive_int callback."""

    def test_positive_value(self):
        """Test that positive values pass."""
        result = validate_positive_int(None, None, 5)
        assert result == 5

    def test_zero_raises(self):
        """Test that zero raises BadParameter."""
        with pytest.raises(click.BadParameter, match="positive integer"):
            validate_positive_int(None, None, 0)

    def test_negative_raises(self):
        """Test that negative raises BadParameter."""
        with pytest.raises(click.BadParameter, match="positive integer"):
            validate_positive_int(None, None, -1)

    def test_none_passes(self):
        """Test that None passes through."""
        assert validate_positive_int(None, None, None) is None


class TestValidateNonNegativeInt:
    """Tests for validate_non_negative_int callback."""

    def test_positive_value(self):
        """Test that positive values pass."""
        result = validate_non_negative_int(None, None, 5)
        assert result == 5

    def test_zero_passes(self):
        """Test that zero passes."""
        result = validate_non_negative_int(None, None, 0)
        assert result == 0

    def test_negative_raises(self):
        """Test that negative raises BadParameter."""
        with pytest.raises(click.BadParameter, match="non-negative"):
            validate_non_negative_int(None, None, -1)


class TestValidateSidCallback:
    """Tests for validate_sid_callback."""

    def test_valid_sid(self):
        """Test valid SID passes."""
        result = validate_sid_callback(None, None, "1703779200.12345")
        assert result == "1703779200.12345"

    def test_invalid_sid(self):
        """Test invalid SID raises BadParameter."""
        # Could raise click.BadParameter or ValidationError
        with pytest.raises((click.BadParameter, Exception)):
            validate_sid_callback(None, None, "invalid-sid")


class TestHandleCliErrors:
    """Tests for handle_cli_errors decorator."""

    def test_validation_error(self):
        """Test ValidationError is handled."""

        @handle_cli_errors
        def failing_func():
            raise ValidationError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 1

    def test_authentication_error(self):
        """Test AuthenticationError is handled."""

        @handle_cli_errors
        def failing_func():
            raise AuthenticationError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 2

    def test_authorization_error(self):
        """Test AuthorizationError is handled."""

        @handle_cli_errors
        def failing_func():
            raise AuthorizationError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 3

    def test_not_found_error(self):
        """Test NotFoundError is handled."""

        @handle_cli_errors
        def failing_func():
            raise NotFoundError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 4

    def test_rate_limit_error(self):
        """Test RateLimitError is handled."""

        @handle_cli_errors
        def failing_func():
            raise RateLimitError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 5

    def test_search_quota_error(self):
        """Test SearchQuotaError is handled."""

        @handle_cli_errors
        def failing_func():
            raise SearchQuotaError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 6

    def test_server_error(self):
        """Test ServerError is handled."""

        @handle_cli_errors
        def failing_func():
            raise ServerError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 7

    def test_splunk_error(self):
        """Test generic SplunkError is handled."""

        @handle_cli_errors
        def failing_func():
            raise SplunkError("test error")

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 1

    def test_keyboard_interrupt(self):
        """Test KeyboardInterrupt is handled."""

        @handle_cli_errors
        def failing_func():
            raise KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            failing_func()
        assert exc_info.value.code == 130

    def test_success_returns_value(self):
        """Test successful function returns value."""

        @handle_cli_errors
        def success_func():
            return "success"

        assert success_func() == "success"


class TestGetTimeBounds:
    """Tests for get_time_bounds function."""

    @patch("splunk_assistant_skills_lib.get_search_defaults")
    def test_uses_provided_values(self, mock_defaults):
        """Test that provided values are used."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        earliest, latest = get_time_bounds("-1h", "-5m")
        assert earliest == "-1h"
        assert latest == "-5m"

    @patch("splunk_assistant_skills_lib.get_search_defaults")
    def test_uses_defaults_when_none(self, mock_defaults):
        """Test that defaults are used when None provided."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        earliest, latest = get_time_bounds(None, None)
        assert earliest == "-24h"
        assert latest == "now"
