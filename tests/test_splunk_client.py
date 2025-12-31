#!/usr/bin/env python3
"""Unit tests for SplunkClient."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from splunk_assistant_skills_lib import SplunkClient


class TestSplunkClientInit:
    """Tests for SplunkClient initialization."""

    def test_init_with_token(self):
        """Test initialization with Bearer token."""
        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        assert client.auth_method == "bearer"
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test-token"

    def test_init_with_basic_auth(self):
        """Test initialization with username/password."""
        client = SplunkClient(
            base_url="https://splunk.example.com",
            username="admin",
            password="password123",
        )
        assert client.auth_method == "basic"
        assert client.session.auth == ("admin", "password123")

    def test_init_without_credentials_raises(self):
        """Test that init without credentials raises ValueError."""
        with pytest.raises(ValueError, match="Must provide either token or username"):
            SplunkClient(base_url="https://splunk.example.com")

    def test_init_normalizes_url(self):
        """Test that URLs are normalized."""
        client = SplunkClient(
            base_url="splunk.example.com/",
            token="test-token",
        )
        assert client.base_url == "https://splunk.example.com:8089/services"

    def test_init_with_custom_port(self):
        """Test initialization with custom port."""
        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
            port=9089,
        )
        assert ":9089" in client.base_url


class TestSplunkClientRequests:
    """Tests for SplunkClient request methods."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
            verify_ssl=False,
        )

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_get_returns_json(self, mock_session_class):
        """Test that get() returns parsed JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        result = client.get("/server/info")

        assert result == {"results": []}
        mock_response.json.assert_called_once()

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_get_raw_returns_bytes(self, mock_session_class):
        """Test that get_raw() returns raw bytes."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"host,count\nserver1,100\nserver2,200\n"

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        result = client.get_raw("/export", params={"output_mode": "csv"})

        assert result == b"host,count\nserver1,100\nserver2,200\n"
        mock_response.json.assert_not_called()

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_get_text_returns_string(self, mock_session_class):
        """Test that get_text() returns string."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<results><result><field>value</field></result></results>"

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        result = client.get_text("/export", params={"output_mode": "xml"})

        assert result == "<results><result><field>value</field></result></results>"
        assert isinstance(result, str)

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_post_raw_returns_bytes(self, mock_session_class):
        """Test that post_raw() returns raw bytes."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"host,count\nserver1,100\n"

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        result = client.post_raw(
            "/search/jobs/export",
            data={"search": "| makeresults"},
            params={"output_mode": "csv"},
        )

        assert result == b"host,count\nserver1,100\n"

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_post_text_returns_string(self, mock_session_class):
        """Test that post_text() returns string."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "host,count\nserver1,100\n"

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        result = client.post_text(
            "/search/jobs/export",
            data={"search": "| makeresults"},
            params={"output_mode": "csv"},
        )

        assert result == "host,count\nserver1,100\n"
        assert isinstance(result, str)


class TestSplunkClientOutputMode:
    """Tests for output_mode handling."""

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_default_output_mode_is_json(self, mock_session_class):
        """Test that default output_mode is json."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        client.get("/server/info")

        # Check that output_mode=json was passed
        call_args = mock_session.request.call_args
        assert call_args[1]["params"]["output_mode"] == "json"

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_explicit_output_mode_is_preserved(self, mock_session_class):
        """Test that explicit output_mode is preserved."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        client.get("/export", params={"output_mode": "csv"})

        # Check that output_mode=csv was preserved
        call_args = mock_session.request.call_args
        assert call_args[1]["params"]["output_mode"] == "csv"

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_raw_methods_preserve_output_mode(self, mock_session_class):
        """Test that raw methods don't override output_mode."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"data"

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        client.get_raw("/export", params={"output_mode": "csv"})

        # Check that output_mode=csv was preserved (not overwritten to json)
        call_args = mock_session.request.call_args
        assert call_args[1]["params"]["output_mode"] == "csv"


class TestUploadLookup:
    """Tests for upload_lookup method."""

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_upload_lookup_adds_csv_extension(self, mock_session_class):
        """Test that upload_lookup adds .csv extension if missing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        client.upload_lookup("test_lookup", "user,email\njohn,john@example.com")

        call_args = mock_session.post.call_args
        assert call_args[1]["data"]["name"] == "test_lookup.csv"

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_upload_lookup_preserves_csv_extension(self, mock_session_class):
        """Test that upload_lookup preserves existing .csv extension."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        client.upload_lookup("test_lookup.csv", "user,email\njohn,john@example.com")

        call_args = mock_session.post.call_args
        assert call_args[1]["data"]["name"] == "test_lookup.csv"

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_upload_lookup_uses_multipart_file_upload(self, mock_session_class):
        """Test that upload_lookup uses multipart file upload with eai:data field."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        csv_content = "user,email\njohn,john@example.com"
        client.upload_lookup("users", csv_content)

        call_args = mock_session.post.call_args
        # Check that files parameter contains eai:data
        assert "files" in call_args[1]
        assert "eai:data" in call_args[1]["files"]
        # The file tuple should be (filename, file_obj, content_type)
        file_tuple = call_args[1]["files"]["eai:data"]
        assert file_tuple[0] == "users.csv"  # filename
        assert file_tuple[2] == "text/csv"  # content_type

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_upload_lookup_uses_correct_endpoint(self, mock_session_class):
        """Test that upload_lookup uses the correct endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        client.upload_lookup("users", "user,email\n", app="my_app", namespace="admin")

        call_args = mock_session.post.call_args
        assert "/servicesNS/admin/my_app/data/lookup-table-files" in call_args[1]["url"]

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_upload_lookup_accepts_bytes_content(self, mock_session_class):
        """Test that upload_lookup accepts bytes content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entry": []}

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        csv_content = b"user,email\njohn,john@example.com"
        client.upload_lookup("users", csv_content)

        call_args = mock_session.post.call_args
        assert "files" in call_args[1]


class TestStreamJsonLines:
    """Tests for stream_json_lines method."""

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_stream_json_lines_parses_each_line(self, mock_session_class):
        """Test that stream_json_lines parses each line as JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            '{"result": {"host": "server1"}}',
            '{"result": {"host": "server2"}}',
            '{"result": {"host": "server3"}}',
        ]

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        results = list(client.stream_json_lines("/export"))

        assert len(results) == 3
        assert results[0] == {"result": {"host": "server1"}}
        assert results[1] == {"result": {"host": "server2"}}
        assert results[2] == {"result": {"host": "server3"}}

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_stream_json_lines_skips_empty_lines(self, mock_session_class):
        """Test that stream_json_lines skips empty lines."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            '{"result": {"host": "server1"}}',
            "",  # Empty line
            '{"result": {"host": "server2"}}',
        ]

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        results = list(client.stream_json_lines("/export"))

        assert len(results) == 2

    @patch("splunk_assistant_skills_lib.splunk_client.requests.Session")
    def test_stream_json_lines_skips_malformed_json(self, mock_session_class):
        """Test that stream_json_lines skips malformed JSON lines."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            '{"result": {"host": "server1"}}',
            "not valid json",
            '{"result": {"host": "server2"}}',
        ]

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        results = list(client.stream_json_lines("/export"))

        assert len(results) == 2


class TestClientProperties:
    """Tests for client properties."""

    def test_is_cloud_returns_true_for_cloud_url(self):
        """Test is_cloud returns True for Splunk Cloud URLs."""
        client = SplunkClient(
            base_url="https://mydeployment.splunkcloud.com",
            token="test-token",
        )
        assert client.is_cloud is True

    def test_is_cloud_returns_false_for_onprem_url(self):
        """Test is_cloud returns False for on-prem URLs."""
        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        assert client.is_cloud is False

    def test_repr(self):
        """Test client repr."""
        client = SplunkClient(
            base_url="https://splunk.example.com",
            token="test-token",
        )
        repr_str = repr(client)
        assert "SplunkClient" in repr_str
        assert "splunk.example.com" in repr_str
        assert "bearer" in repr_str
