"""Tests for the Splunk Assistant Skills CLI."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from splunk_as.cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_client():
    """Create a mock Splunk client."""
    client = MagicMock()
    client.get.return_value = {"entry": [{"content": {}}]}
    client.post.return_value = {"results": [], "sid": "1703779200.12345"}
    return client


class TestCLIMain:
    """Tests for the main CLI entry point."""

    def test_help(self, runner):
        """Test --help flag shows usage."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Splunk Assistant Skills CLI" in result.output
        assert "search" in result.output
        assert "job" in result.output

    def test_version(self, runner):
        """Test --version flag shows version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "splunk-as" in result.output

    def test_no_command_shows_help(self, runner):
        """Test that invoking without command shows help."""
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_invalid_command(self, runner):
        """Test invalid command shows error."""
        result = runner.invoke(cli, ["invalid_command"])
        assert result.exit_code != 0


class TestSearchCommands:
    """Tests for search command group."""

    def test_search_help(self, runner):
        """Test search --help."""
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "oneshot" in result.output
        assert "normal" in result.output
        assert "blocking" in result.output
        assert "validate" in result.output
        assert "results" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.cli.commands.search_cmds.get_api_settings")
    @patch("splunk_as.get_search_defaults")
    def test_search_oneshot(
        self, mock_defaults, mock_api, mock_get_client, runner, mock_client
    ):
        """Test search oneshot command."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_api.return_value = {"search_timeout": 300}
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [{"host": "server1", "count": "10"}]
        }

        result = runner.invoke(cli, ["search", "oneshot", "index=main | head 10"])

        assert result.exit_code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/search/jobs/oneshot" in call_args[0]

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.cli.commands.search_cmds.get_api_settings")
    @patch("splunk_as.get_search_defaults")
    def test_search_oneshot_with_time_bounds(
        self, mock_defaults, mock_api, mock_get_client, runner, mock_client
    ):
        """Test search oneshot with time options."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_api.return_value = {"search_timeout": 300}
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"results": []}

        result = runner.invoke(
            cli,
            [
                "search",
                "oneshot",
                "index=main",
                "--earliest",
                "-1h",
                "--latest",
                "now",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["data"]["earliest_time"] == "-1h"
        assert call_kwargs["data"]["latest_time"] == "now"

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.cli.commands.search_cmds.get_api_settings")
    @patch("splunk_as.get_search_defaults")
    def test_search_oneshot_json_output(
        self, mock_defaults, mock_api, mock_get_client, runner, mock_client
    ):
        """Test search oneshot with JSON output."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_api.return_value = {"search_timeout": 300}
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"results": [{"host": "server1"}]}

        result = runner.invoke(
            cli, ["search", "oneshot", "index=main", "--output", "json"]
        )

        assert result.exit_code == 0
        assert '"host"' in result.output or "server1" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.get_search_defaults")
    def test_search_normal(self, mock_defaults, mock_get_client, runner, mock_client):
        """Test search normal command."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"sid": "1703779200.12345"}

        result = runner.invoke(cli, ["search", "normal", "index=main | stats count"])

        assert result.exit_code == 0
        assert "1703779200.12345" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.cli.commands.search_cmds.wait_for_job")
    @patch("splunk_as.get_search_defaults")
    def test_search_normal_with_wait(
        self, mock_defaults, mock_wait, mock_get_client, runner, mock_client
    ):
        """Test search normal with --wait flag."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"sid": "1703779200.12345"}
        mock_client.get.return_value = {"results": [{"count": "42"}]}
        mock_wait.return_value = MagicMock(result_count=1)

        result = runner.invoke(
            cli, ["search", "normal", "index=main | stats count", "--wait"]
        )

        assert result.exit_code == 0
        mock_wait.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.get_search_defaults")
    def test_search_blocking(self, mock_defaults, mock_get_client, runner, mock_client):
        """Test search blocking command."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"entry": [{"name": "1703779200.12345"}]}
        mock_client.get.return_value = {"results": [{"count": "42"}]}

        result = runner.invoke(cli, ["search", "blocking", "index=main | head 10"])

        assert result.exit_code == 0

    def test_search_validate(self, runner):
        """Test search validate command."""
        result = runner.invoke(
            cli, ["search", "validate", "index=main | stats count by host"]
        )

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_search_validate_with_suggestions(self, runner):
        """Test search validate with suggestions flag."""
        result = runner.invoke(
            cli, ["search", "validate", "index=main", "--suggestions"]
        )

        assert result.exit_code == 0

    def test_search_validate_invalid_spl(self, runner):
        """Test search validate with invalid SPL."""
        result = runner.invoke(cli, ["search", "validate", "index=main |"])

        assert result.exit_code == 0
        # Should report the issue but not crash

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_search_results(self, mock_get_client, runner, mock_client):
        """Test search results command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {"results": [{"host": "server1"}]}

        result = runner.invoke(cli, ["search", "results", "1703779200.12345"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_search_preview(self, mock_get_client, runner, mock_client):
        """Test search preview command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {"results": [{"host": "server1"}]}

        result = runner.invoke(cli, ["search", "preview", "1703779200.12345"])

        assert result.exit_code == 0
        assert "preview" in result.output.lower()


class TestJobCommands:
    """Tests for job command group."""

    def test_job_help(self, runner):
        """Test job --help."""
        result = runner.invoke(cli, ["job", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "status" in result.output
        assert "cancel" in result.output
        assert "list" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_job_list(self, mock_get_client, runner, mock_client):
        """Test job list command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "1703779200.12345",
                    "content": {
                        "dispatchState": "DONE",
                        "resultCount": 100,
                        "runDuration": 1.5,
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["job", "list"])

        assert result.exit_code == 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_job_status(self, mock_get_client, runner, mock_client):
        """Test job status command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "1703779200.12345",
                    "content": {
                        "dispatchState": "DONE",
                        "doneProgress": 1.0,
                        "resultCount": 42,
                        "eventCount": 1000,
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["job", "status", "1703779200.12345"])

        assert result.exit_code == 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_job_cancel(self, mock_get_client, runner, mock_client):
        """Test job cancel command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(cli, ["job", "cancel", "1703779200.12345"])

        assert result.exit_code == 0
        mock_client.post.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_job_pause(self, mock_get_client, runner, mock_client):
        """Test job pause command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(cli, ["job", "pause", "1703779200.12345"])

        assert result.exit_code == 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_job_delete(self, mock_get_client, runner, mock_client):
        """Test job delete command."""
        mock_get_client.return_value = mock_client
        mock_client.delete.return_value = {}

        result = runner.invoke(cli, ["job", "delete", "1703779200.12345"])

        assert result.exit_code == 0


class TestMetadataCommands:
    """Tests for metadata command group."""

    def test_metadata_help(self, runner):
        """Test metadata --help."""
        result = runner.invoke(cli, ["metadata", "--help"])
        assert result.exit_code == 0
        assert "indexes" in result.output
        assert "sourcetypes" in result.output
        assert "sources" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_metadata_indexes(self, mock_get_client, runner, mock_client):
        """Test metadata indexes command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {"name": "main", "content": {"totalEventCount": 1000}},
                {"name": "_internal", "content": {"totalEventCount": 500}},
            ]
        }

        result = runner.invoke(cli, ["metadata", "indexes"])

        assert result.exit_code == 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_metadata_sourcetypes(self, mock_get_client, runner, mock_client):
        """Test metadata sourcetypes command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [
                {"sourcetype": "syslog", "count": "1000"},
                {"sourcetype": "access_combined", "count": "500"},
            ]
        }

        result = runner.invoke(cli, ["metadata", "sourcetypes"])

        assert result.exit_code == 0


class TestAdminCommands:
    """Tests for admin command group."""

    def test_admin_help(self, runner):
        """Test admin --help."""
        result = runner.invoke(cli, ["admin", "--help"])
        assert result.exit_code == 0
        assert "info" in result.output
        assert "status" in result.output
        assert "health" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_admin_info(self, mock_get_client, runner, mock_client):
        """Test admin info command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "content": {
                        "serverName": "splunk-server",
                        "version": "9.1.0",
                        "build": "12345",
                        "os_name": "Linux",
                    }
                }
            ]
        }

        result = runner.invoke(cli, ["admin", "info"])

        assert result.exit_code == 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_admin_health(self, mock_get_client, runner, mock_client):
        """Test admin health command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [{"content": {"health": "green", "features": {}}}]
        }

        result = runner.invoke(cli, ["admin", "health"])

        assert result.exit_code == 0


class TestSecurityCommands:
    """Tests for security command group."""

    def test_security_help(self, runner):
        """Test security --help."""
        result = runner.invoke(cli, ["security", "--help"])
        assert result.exit_code == 0
        assert "whoami" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_security_whoami(self, mock_get_client, runner, mock_client):
        """Test security whoami command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "admin",
                    "content": {
                        "realname": "Administrator",
                        "roles": ["admin", "power"],
                        "email": "admin@example.com",
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["security", "whoami"])

        assert result.exit_code == 0


class TestAppCommands:
    """Tests for app command group."""

    def test_app_help(self, runner):
        """Test app --help."""
        result = runner.invoke(cli, ["app", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "get" in result.output
        assert "enable" in result.output
        assert "disable" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_app_list(self, mock_get_client, runner, mock_client):
        """Test app list command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "search",
                    "content": {
                        "label": "Search & Reporting",
                        "version": "9.1.0",
                        "disabled": False,
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["app", "list"])

        assert result.exit_code == 0


class TestAlertCommands:
    """Tests for alert command group."""

    def test_alert_help(self, runner):
        """Test alert --help."""
        result = runner.invoke(cli, ["alert", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "triggered" in result.output


class TestExportCommands:
    """Tests for export command group."""

    def test_export_help(self, runner):
        """Test export --help."""
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        assert "results" in result.output
        assert "estimate" in result.output


class TestLookupCommands:
    """Tests for lookup command group."""

    def test_lookup_help(self, runner):
        """Test lookup --help."""
        result = runner.invoke(cli, ["lookup", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "get" in result.output
        assert "upload" in result.output


class TestSavedsearchCommands:
    """Tests for savedsearch command group."""

    def test_savedsearch_help(self, runner):
        """Test savedsearch --help."""
        result = runner.invoke(cli, ["savedsearch", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "get" in result.output
        assert "create" in result.output
        assert "run" in result.output


class TestKVStoreCommands:
    """Tests for kvstore command group."""

    def test_kvstore_help(self, runner):
        """Test kvstore --help."""
        result = runner.invoke(cli, ["kvstore", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output


class TestTagCommands:
    """Tests for tag command group."""

    def test_tag_help(self, runner):
        """Test tag --help."""
        result = runner.invoke(cli, ["tag", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "add" in result.output
        assert "remove" in result.output
        assert "search" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_list(self, mock_get_client, runner, mock_client):
        """Test tag list command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [
                {"title": "production", "eai:acl.app": "search"},
                {"title": "staging", "eai:acl.app": "search"},
            ]
        }

        result = runner.invoke(cli, ["tag", "list"])

        assert result.exit_code == 0
        mock_client.post.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_list_with_app_filter(self, mock_get_client, runner, mock_client):
        """Test tag list with --app filter."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [
                {"title": "production", "eai:acl.app": "search"},
                {"title": "staging", "eai:acl.app": "myapp"},
            ]
        }

        result = runner.invoke(cli, ["tag", "list", "--app", "search"])

        assert result.exit_code == 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_list_json_output(self, mock_get_client, runner, mock_client):
        """Test tag list with JSON output."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [{"title": "production", "eai:acl.app": "search"}]
        }

        result = runner.invoke(cli, ["tag", "list", "-o", "json"])

        assert result.exit_code == 0
        assert "[" in result.output  # JSON array

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_list_empty(self, mock_get_client, runner, mock_client):
        """Test tag list with no tags."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"results": []}

        result = runner.invoke(cli, ["tag", "list"])

        assert result.exit_code == 0
        assert "No tags found" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_add(self, mock_get_client, runner, mock_client):
        """Test tag add command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(cli, ["tag", "add", "host::webserver01", "production"])

        assert result.exit_code == 0
        assert "Added tag" in result.output
        mock_client.post.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_add_with_app(self, mock_get_client, runner, mock_client):
        """Test tag add with --app option."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(
            cli, ["tag", "add", "host::webserver01", "production", "--app", "myapp"]
        )

        assert result.exit_code == 0
        call_args = mock_client.post.call_args
        assert "/myapp/" in call_args[0][0]

    def test_tag_add_invalid_format(self, runner):
        """Test tag add with invalid field_value_pair format."""
        result = runner.invoke(cli, ["tag", "add", "invalid_format", "production"])

        # Command returns non-zero exit code for invalid format
        assert "field::value" in result.output or result.exit_code != 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_remove(self, mock_get_client, runner, mock_client):
        """Test tag remove command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(cli, ["tag", "remove", "host::webserver01", "production"])

        assert result.exit_code == 0
        assert "Removed tag" in result.output
        mock_client.post.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_remove_with_app(self, mock_get_client, runner, mock_client):
        """Test tag remove with --app option."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(
            cli, ["tag", "remove", "host::webserver01", "production", "--app", "myapp"]
        )

        assert result.exit_code == 0
        call_args = mock_client.post.call_args
        assert "/myapp/" in call_args[0][0]

    def test_tag_remove_invalid_format(self, runner):
        """Test tag remove with invalid field_value_pair format."""
        result = runner.invoke(cli, ["tag", "remove", "invalid_format", "production"])

        # Command returns non-zero exit code for invalid format
        assert "field::value" in result.output or result.exit_code != 0

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_search(self, mock_get_client, runner, mock_client):
        """Test tag search command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [
                {"host": "webserver01", "_time": "2025-01-31T10:00:00"},
                {"host": "webserver02", "_time": "2025-01-31T10:05:00"},
            ]
        }

        result = runner.invoke(cli, ["tag", "search", "production"])

        assert result.exit_code == 0
        mock_client.post.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_search_with_index(self, mock_get_client, runner, mock_client):
        """Test tag search with --index filter."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"results": []}

        result = runner.invoke(cli, ["tag", "search", "production", "--index", "main"])

        assert result.exit_code == 0
        call_args = mock_client.post.call_args[1]
        assert 'index="main"' in call_args["data"]["search"]

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_search_with_earliest(self, mock_get_client, runner, mock_client):
        """Test tag search with --earliest option."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"results": []}

        result = runner.invoke(
            cli, ["tag", "search", "production", "--earliest", "-1h"]
        )

        assert result.exit_code == 0
        call_args = mock_client.post.call_args[1]
        assert call_args["data"]["earliest_time"] == "-1h"

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_search_json_output(self, mock_get_client, runner, mock_client):
        """Test tag search with JSON output."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [{"host": "webserver01"}]
        }

        result = runner.invoke(cli, ["tag", "search", "production", "-o", "json"])

        assert result.exit_code == 0
        assert "[" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_tag_search_no_results(self, mock_get_client, runner, mock_client):
        """Test tag search with no results."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"results": []}

        result = runner.invoke(cli, ["tag", "search", "nonexistent"])

        assert result.exit_code == 0
        assert "No events found" in result.output


class TestMetricsCommands:
    """Tests for metrics command group."""

    def test_metrics_help(self, runner):
        """Test metrics --help."""
        result = runner.invoke(cli, ["metrics", "--help"])
        assert result.exit_code == 0
        assert "mpreview" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_metrics_mpreview(self, mock_get_client, runner, mock_client):
        """Test metrics mpreview command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "results": [
                {
                    "metric_name": "cpu.percent",
                    "_value": "45.2",
                    "_time": "2025-01-31T10:00:00",
                },
            ]
        }

        result = runner.invoke(
            cli, ["metrics", "mpreview", "cpu.percent", "--index", "metrics"]
        )

        assert result.exit_code == 0
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "mpreview" in call_args[1]["data"]["search"]

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_metrics_mpreview_with_filter(self, mock_get_client, runner, mock_client):
        """Test metrics mpreview with filter expression."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"results": []}

        result = runner.invoke(
            cli,
            [
                "metrics",
                "mpreview",
                "cpu.percent",
                "--filter",
                "host=server1",
                "--count",
                "50",
            ],
        )

        assert result.exit_code == 0

    def test_metrics_mpreview_invalid_metric_name(self, runner):
        """Test metrics mpreview rejects invalid metric names."""
        result = runner.invoke(
            cli, ["metrics", "mpreview", "invalid;metric", "--index", "metrics"]
        )
        # Should fail validation
        assert result.exit_code != 0 or "Invalid" in result.output


class TestAppInstallCommand:
    """Tests for app install command."""

    def test_app_install_help(self, runner):
        """Test app install --help."""
        result = runner.invoke(cli, ["app", "install", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--update" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_app_install_success(self, mock_get_client, runner, mock_client, tmp_path):
        """Test app install command."""
        mock_get_client.return_value = mock_client
        mock_client.upload_file.return_value = {"entry": [{"name": "my_app"}]}

        # Create a dummy package file
        package_file = tmp_path / "my_app.tar.gz"
        package_file.write_bytes(b"fake package content")

        result = runner.invoke(cli, ["app", "install", str(package_file)])

        assert result.exit_code == 0
        assert "Installed app: my_app" in result.output
        mock_client.upload_file.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_app_install_with_name_override(
        self, mock_get_client, runner, mock_client, tmp_path
    ):
        """Test app install with --name option."""
        mock_get_client.return_value = mock_client
        mock_client.upload_file.return_value = {"entry": [{"name": "custom_name"}]}

        package_file = tmp_path / "package.spl"
        package_file.write_bytes(b"fake package content")

        result = runner.invoke(
            cli, ["app", "install", str(package_file), "--name", "custom_name"]
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.upload_file.call_args[1]
        assert call_kwargs["data"]["explicit_appname"] == "custom_name"

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_app_install_with_update_flag(
        self, mock_get_client, runner, mock_client, tmp_path
    ):
        """Test app install with --update flag."""
        mock_get_client.return_value = mock_client
        mock_client.upload_file.return_value = {"entry": [{"name": "my_app"}]}

        package_file = tmp_path / "my_app.tgz"
        package_file.write_bytes(b"fake package content")

        result = runner.invoke(cli, ["app", "install", str(package_file), "--update"])

        assert result.exit_code == 0
        call_kwargs = mock_client.upload_file.call_args[1]
        assert call_kwargs["data"]["update"] == "true"

    def test_app_install_path_traversal_rejected(self, runner):
        """Test app install rejects path traversal attempts."""
        result = runner.invoke(cli, ["app", "install", "../../../etc/passwd"])

        assert (
            result.exit_code != 0
            or "Invalid" in result.output
            or "traversal" in result.output.lower()
        )


class TestExportStreamCommand:
    """Tests for export stream command."""

    def test_export_stream_help(self, runner):
        """Test export stream --help."""
        result = runner.invoke(cli, ["export", "stream", "--help"])
        assert result.exit_code == 0
        assert "json_rows" in result.output
        assert "--fields" in result.output
        assert "--count" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.cli.commands.export_cmds.get_api_settings")
    @patch("splunk_as.get_search_defaults")
    def test_export_stream_csv(
        self, mock_defaults, mock_api, mock_get_client, runner, mock_client, tmp_path
    ):
        """Test export stream command with CSV format."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_api.return_value = {"search_timeout": 300}
        mock_get_client.return_value = mock_client
        mock_client.stream_results.return_value = iter(
            [b"host,count\n", b"server1,10\n"]
        )

        output_file = tmp_path / "output.csv"

        result = runner.invoke(
            cli,
            [
                "export",
                "stream",
                "index=main | stats count by host",
                "-o",
                str(output_file),
            ],
        )

        assert result.exit_code == 0
        assert "Exported" in result.output
        mock_client.stream_results.assert_called_once()
        call_args = mock_client.stream_results.call_args
        assert "/search/jobs/export" in call_args[0]

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.cli.commands.export_cmds.get_api_settings")
    @patch("splunk_as.get_search_defaults")
    def test_export_stream_json_rows(
        self, mock_defaults, mock_api, mock_get_client, runner, mock_client, tmp_path
    ):
        """Test export stream with json_rows format."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_api.return_value = {"search_timeout": 300}
        mock_get_client.return_value = mock_client
        mock_client.stream_results.return_value = iter([b'[{"host":"server1"}]'])

        output_file = tmp_path / "output.json"

        result = runner.invoke(
            cli,
            [
                "export",
                "stream",
                "index=main",
                "-o",
                str(output_file),
                "-f",
                "json_rows",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.stream_results.call_args[1]
        assert call_kwargs["params"]["output_mode"] == "json_rows"

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    @patch("splunk_as.cli.commands.export_cmds.get_api_settings")
    @patch("splunk_as.get_search_defaults")
    def test_export_stream_with_options(
        self, mock_defaults, mock_api, mock_get_client, runner, mock_client, tmp_path
    ):
        """Test export stream with time bounds and field options."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_api.return_value = {"search_timeout": 300}
        mock_get_client.return_value = mock_client
        mock_client.stream_results.return_value = iter([b"data"])

        output_file = tmp_path / "output.csv"

        result = runner.invoke(
            cli,
            [
                "export",
                "stream",
                "index=main",
                "-o",
                str(output_file),
                "-e",
                "-1h",
                "-l",
                "now",
                "--fields",
                "host,source",
                "--count",
                "1000",
            ],
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.stream_results.call_args[1]
        assert call_kwargs["params"]["field_list"] == "host,source"
        assert call_kwargs["params"]["count"] == 1000


class TestExportJsonRowsFormat:
    """Tests for json_rows output format in export commands."""

    def test_export_results_json_rows_option(self, runner):
        """Test export results shows json_rows option."""
        result = runner.invoke(cli, ["export", "results", "--help"])
        assert result.exit_code == 0
        assert "json_rows" in result.output

    def test_export_job_json_rows_option(self, runner):
        """Test export job shows json_rows option."""
        result = runner.invoke(cli, ["export", "job", "--help"])
        assert result.exit_code == 0
        assert "json_rows" in result.output


class TestKVStoreTruncateCommand:
    """Tests for kvstore truncate command."""

    def test_kvstore_truncate_help(self, runner):
        """Test kvstore truncate --help."""
        result = runner.invoke(cli, ["kvstore", "truncate", "--help"])
        assert result.exit_code == 0
        assert "Delete all records" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_kvstore_truncate_with_force(self, mock_get_client, runner, mock_client):
        """Test kvstore truncate with --force flag."""
        mock_get_client.return_value = mock_client
        mock_client.delete.return_value = {}

        result = runner.invoke(cli, ["kvstore", "truncate", "my_collection", "--force"])

        assert result.exit_code == 0
        assert "Truncated" in result.output
        mock_client.delete.assert_called_once()

    def test_kvstore_truncate_requires_confirmation(self, runner):
        """Test kvstore truncate requires confirmation without --force."""
        result = runner.invoke(
            cli, ["kvstore", "truncate", "my_collection"], input="n\n"
        )
        assert "Cancelled" in result.output


class TestKVStoreBatchInsertCommand:
    """Tests for kvstore batch-insert command."""

    def test_kvstore_batch_insert_help(self, runner):
        """Test kvstore batch-insert --help."""
        result = runner.invoke(cli, ["kvstore", "batch-insert", "--help"])
        assert result.exit_code == 0
        assert "JSON file" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_kvstore_batch_insert_success(
        self, mock_get_client, runner, mock_client, tmp_path
    ):
        """Test kvstore batch-insert command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        # Create a test JSON file
        json_file = tmp_path / "records.json"
        json_file.write_text('[{"name": "test1"}, {"name": "test2"}]')

        result = runner.invoke(
            cli, ["kvstore", "batch-insert", "my_collection", str(json_file)]
        )

        assert result.exit_code == 0
        assert "Inserted 2 records" in result.output


class TestSavedSearchHistoryCommand:
    """Tests for savedsearch history command."""

    def test_savedsearch_history_help(self, runner):
        """Test savedsearch history --help."""
        result = runner.invoke(cli, ["savedsearch", "history", "--help"])
        assert result.exit_code == 0
        assert "run history" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_savedsearch_history(self, mock_get_client, runner, mock_client):
        """Test savedsearch history command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "1703779200.12345",
                    "published": "2025-01-31T10:00:00",
                    "content": {
                        "dispatchState": "DONE",
                        "resultCount": 42,
                        "runDuration": 1.5,
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["savedsearch", "history", "My Report"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()


class TestLookupTransformsCommand:
    """Tests for lookup transforms command."""

    def test_lookup_transforms_help(self, runner):
        """Test lookup transforms --help."""
        result = runner.invoke(cli, ["lookup", "transforms", "--help"])
        assert result.exit_code == 0
        assert "transform definitions" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_lookup_transforms_list(self, mock_get_client, runner, mock_client):
        """Test lookup transforms command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "my_lookup",
                    "acl": {"app": "search"},
                    "content": {
                        "filename": "my_lookup.csv",
                        "match_type": "WILDCARD",
                        "max_matches": "1",
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["lookup", "transforms"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()


class TestDashboardCommands:
    """Tests for dashboard commands."""

    def test_dashboard_help(self, runner):
        """Test dashboard --help."""
        result = runner.invoke(cli, ["dashboard", "--help"])
        assert result.exit_code == 0
        assert "Dashboard management" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_dashboard_list(self, mock_get_client, runner, mock_client):
        """Test dashboard list command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "my_dashboard",
                    "acl": {"app": "search"},
                    "content": {
                        "label": "My Dashboard",
                        "isDashboard": True,
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["dashboard", "list"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_dashboard_get(self, mock_get_client, runner, mock_client):
        """Test dashboard get command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "my_dashboard",
                    "acl": {"app": "search", "owner": "admin"},
                    "content": {
                        "label": "My Dashboard",
                        "isDashboard": True,
                        "eai:data": "<dashboard><label>My Dashboard</label></dashboard>",
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["dashboard", "get", "my_dashboard"])

        assert result.exit_code == 0
        assert "my_dashboard" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_dashboard_export(self, mock_get_client, runner, mock_client, tmp_path):
        """Test dashboard export command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "my_dashboard",
                    "content": {
                        "eai:data": "<dashboard><label>Test</label></dashboard>",
                    },
                }
            ]
        }

        output_file = tmp_path / "dashboard.xml"
        result = runner.invoke(
            cli, ["dashboard", "export", "my_dashboard", "-o", str(output_file)]
        )

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Exported" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_dashboard_delete_requires_confirmation(
        self, mock_get_client, runner, mock_client
    ):
        """Test dashboard delete requires confirmation without --force."""
        result = runner.invoke(
            cli, ["dashboard", "delete", "my_dashboard"], input="n\n"
        )
        assert "Cancelled" in result.output


class TestInputCommands:
    """Tests for data input commands."""

    def test_input_help(self, runner):
        """Test input --help."""
        result = runner.invoke(cli, ["input", "--help"])
        assert result.exit_code == 0
        assert "Data input management" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_input_hec_list(self, mock_get_client, runner, mock_client):
        """Test input hec list command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "my_token",
                    "content": {
                        "disabled": False,
                        "index": "main",
                        "sourcetype": "json",
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["input", "hec", "list"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_input_hec_create(self, mock_get_client, runner, mock_client):
        """Test input hec create command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {
            "entry": [
                {
                    "name": "new_token",
                    "content": {
                        "token": "abc123-token-value",
                    },
                }
            ]
        }

        result = runner.invoke(
            cli, ["input", "hec", "create", "new_token", "--index", "main"]
        )

        assert result.exit_code == 0
        assert "Created" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_input_monitor_list(self, mock_get_client, runner, mock_client):
        """Test input monitor list command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "/var/log/messages",
                    "content": {
                        "disabled": False,
                        "index": "main",
                        "sourcetype": "syslog",
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["input", "monitor", "list"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_input_summary(self, mock_get_client, runner, mock_client):
        """Test input summary command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {"entry": [{"name": "test"}]}

        result = runner.invoke(cli, ["input", "summary"])

        assert result.exit_code == 0
        assert "Summary" in result.output


class TestUserCommands:
    """Tests for user and role commands."""

    def test_user_help(self, runner):
        """Test user --help."""
        result = runner.invoke(cli, ["user", "--help"])
        assert result.exit_code == 0
        assert "User and role management" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_user_list(self, mock_get_client, runner, mock_client):
        """Test user list command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "admin",
                    "content": {
                        "realname": "Admin User",
                        "email": "admin@example.com",
                        "roles": ["admin", "power"],
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["user", "list"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_user_get(self, mock_get_client, runner, mock_client):
        """Test user get command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "admin",
                    "content": {
                        "realname": "Admin User",
                        "email": "admin@example.com",
                        "roles": ["admin"],
                        "defaultApp": "search",
                        "type": "Splunk",
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["user", "get", "admin"])

        assert result.exit_code == 0
        assert "admin" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_user_create(self, mock_get_client, runner, mock_client):
        """Test user create command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(
            cli, ["user", "create", "newuser", "-p", "password123", "-r", "user"]
        )

        assert result.exit_code == 0
        assert "Created" in result.output

    def test_user_delete_requires_confirmation(self, runner):
        """Test user delete requires confirmation without --force."""
        result = runner.invoke(cli, ["user", "delete", "testuser"], input="n\n")
        assert "Cancelled" in result.output

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_role_list(self, mock_get_client, runner, mock_client):
        """Test user role list command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "admin",
                    "content": {
                        "imported_roles": ["power", "user"],
                        "defaultApp": "launcher",
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["user", "role", "list"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()

    @patch("splunk_as.cli.cli_utils.get_splunk_client")
    def test_role_get(self, mock_get_client, runner, mock_client):
        """Test user role get command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {
            "entry": [
                {
                    "name": "admin",
                    "content": {
                        "defaultApp": "launcher",
                        "imported_roles": ["power"],
                        "capabilities": ["admin_all_objects", "change_own_password"],
                    },
                }
            ]
        }

        result = runner.invoke(cli, ["user", "role", "get", "admin"])

        assert result.exit_code == 0
        assert "admin" in result.output


class TestConfigCommands:
    """Tests for config commands."""

    def test_config_help(self, runner):
        """Test config --help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Configuration management" in result.output

    def test_config_show(self, runner):
        """Test config show command."""
        result = runner.invoke(cli, ["config", "show"])

        assert result.exit_code == 0
        assert "Configuration" in result.output

    def test_config_show_json(self, runner):
        """Test config show --output json."""
        result = runner.invoke(cli, ["config", "show", "-o", "json"])

        assert result.exit_code == 0
        # Should be valid JSON
        assert "{" in result.output

    def test_config_sources(self, runner):
        """Test config sources command."""
        result = runner.invoke(cli, ["config", "sources"])

        assert result.exit_code == 0
        assert "Configuration Sources" in result.output
        assert "Environment Variables" in result.output


class TestCompletionCommands:
    """Tests for shell completion commands."""

    def test_completion_help(self, runner):
        """Test completion --help."""
        result = runner.invoke(cli, ["completion", "--help"])
        assert result.exit_code == 0
        assert "Shell completion support" in result.output

    def test_completion_bash(self, runner):
        """Test completion bash command."""
        result = runner.invoke(cli, ["completion", "bash"])

        assert result.exit_code == 0
        assert "_SPLUNK_AS_COMPLETE" in result.output
        assert "bash_source" in result.output

    def test_completion_zsh(self, runner):
        """Test completion zsh command."""
        result = runner.invoke(cli, ["completion", "zsh"])

        assert result.exit_code == 0
        assert "_SPLUNK_AS_COMPLETE" in result.output
        assert "zsh_source" in result.output

    def test_completion_fish(self, runner):
        """Test completion fish command."""
        result = runner.invoke(cli, ["completion", "fish"])

        assert result.exit_code == 0
        assert "_SPLUNK_AS_COMPLETE" in result.output
        assert "fish_source" in result.output

    def test_completion_install(self, runner):
        """Test completion install command."""
        result = runner.invoke(cli, ["completion", "install"])

        assert result.exit_code == 0
        assert "Detected shell" in result.output
