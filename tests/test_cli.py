"""Tests for the Splunk Assistant Skills CLI."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from splunk_assistant_skills_lib.cli.main import cli


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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    @patch("splunk_assistant_skills_lib.cli.commands.search_cmds.get_api_settings")
    @patch("splunk_assistant_skills_lib.get_search_defaults")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    @patch("splunk_assistant_skills_lib.cli.commands.search_cmds.get_api_settings")
    @patch("splunk_assistant_skills_lib.get_search_defaults")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    @patch("splunk_assistant_skills_lib.cli.commands.search_cmds.get_api_settings")
    @patch("splunk_assistant_skills_lib.get_search_defaults")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    @patch("splunk_assistant_skills_lib.get_search_defaults")
    def test_search_normal(self, mock_defaults, mock_get_client, runner, mock_client):
        """Test search normal command."""
        mock_defaults.return_value = {"earliest_time": "-24h", "latest_time": "now"}
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {"sid": "1703779200.12345"}

        result = runner.invoke(cli, ["search", "normal", "index=main | stats count"])

        assert result.exit_code == 0
        assert "1703779200.12345" in result.output

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    @patch("splunk_assistant_skills_lib.cli.commands.search_cmds.wait_for_job")
    @patch("splunk_assistant_skills_lib.get_search_defaults")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    @patch("splunk_assistant_skills_lib.get_search_defaults")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    def test_search_results(self, mock_get_client, runner, mock_client):
        """Test search results command."""
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = {"results": [{"host": "server1"}]}

        result = runner.invoke(cli, ["search", "results", "1703779200.12345"])

        assert result.exit_code == 0
        mock_client.get.assert_called_once()

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    def test_job_cancel(self, mock_get_client, runner, mock_client):
        """Test job cancel command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(cli, ["job", "cancel", "1703779200.12345"])

        assert result.exit_code == 0
        mock_client.post.assert_called_once()

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
    def test_job_pause(self, mock_get_client, runner, mock_client):
        """Test job pause command."""
        mock_get_client.return_value = mock_client
        mock_client.post.return_value = {}

        result = runner.invoke(cli, ["job", "pause", "1703779200.12345"])

        assert result.exit_code == 0

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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

    @patch("splunk_assistant_skills_lib.cli.cli_utils.get_splunk_client")
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


class TestMetricsCommands:
    """Tests for metrics command group."""

    def test_metrics_help(self, runner):
        """Test metrics --help."""
        result = runner.invoke(cli, ["metrics", "--help"])
        assert result.exit_code == 0
