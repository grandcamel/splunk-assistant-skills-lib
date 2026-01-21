"""Tests for the mock client system."""

import os
import pytest
from unittest.mock import patch

from splunk_as.mock import (
    MockSplunkClient,
    MockSplunkClientBase,
    MockSearchClient,
    MockJobClient,
    MockMetadataClient,
    MockAdminClient,
    MockExportClient,
    MockSearchJobClient,
    MockSearchExportClient,
    MockFullSearchClient,
    is_mock_mode,
    create_mock_client,
    create_cloud_mock,
    create_minimal_mock,
    SearchMixin,
    JobMixin,
    MetadataMixin,
    AdminMixin,
    ExportMixin,
    ResponseFactory,
    JobFactory,
    IndexFactory,
    UserFactory,
    TimestampFactory,
    ResultFactory,
)
from splunk_as.mock.mixins.job import MockJobState


class TestIsMockMode:
    """Tests for is_mock_mode function."""

    def test_returns_true_when_env_set_true(self):
        with patch.dict(os.environ, {"SPLUNK_MOCK_MODE": "true"}):
            assert is_mock_mode() is True

    def test_returns_true_when_env_set_TRUE(self):
        with patch.dict(os.environ, {"SPLUNK_MOCK_MODE": "TRUE"}):
            assert is_mock_mode() is True

    def test_returns_false_when_env_set_false(self):
        with patch.dict(os.environ, {"SPLUNK_MOCK_MODE": "false"}):
            assert is_mock_mode() is False

    def test_returns_false_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SPLUNK_MOCK_MODE", None)
            assert is_mock_mode() is False

    def test_returns_false_for_empty_string(self):
        with patch.dict(os.environ, {"SPLUNK_MOCK_MODE": ""}):
            assert is_mock_mode() is False


class TestMockSplunkClientBase:
    """Tests for MockSplunkClientBase."""

    def test_default_initialization(self):
        client = MockSplunkClientBase()
        assert "mock-splunk.example.com" in client.base_url
        assert client.auth_method == "bearer"
        assert client.port == 8089

    def test_custom_base_url(self):
        client = MockSplunkClientBase(base_url="https://custom.example.com")
        assert "custom.example.com" in client.base_url

    def test_basic_auth_initialization(self):
        client = MockSplunkClientBase(token=None, username="admin", password="pass")
        assert client.auth_method == "basic"

    def test_context_manager(self):
        with MockSplunkClientBase() as client:
            assert client is not None
        # close() should be called

    def test_close(self):
        client = MockSplunkClientBase()
        client.close()  # Should not raise

    def test_get_records_call(self):
        client = MockSplunkClientBase()
        client.get("/some/endpoint", params={"foo": "bar"})
        assert len(client.calls) == 1
        assert client.calls[0]["method"] == "GET"
        assert client.calls[0]["endpoint"] == "/some/endpoint"

    def test_post_records_call(self):
        client = MockSplunkClientBase()
        client.post("/some/endpoint", data={"key": "value"})
        assert len(client.calls) == 1
        assert client.calls[0]["method"] == "POST"
        assert client.calls[0]["data"] == {"key": "value"}

    def test_put_records_call(self):
        client = MockSplunkClientBase()
        client.put("/some/endpoint", data={"key": "value"})
        assert client.calls[0]["method"] == "PUT"

    def test_delete_records_call(self):
        client = MockSplunkClientBase()
        client.delete("/some/endpoint")
        assert client.calls[0]["method"] == "DELETE"

    def test_set_response_override(self):
        client = MockSplunkClientBase()
        client.set_response("/test", {"custom": "response"})
        result = client.get("/test")
        assert result == {"custom": "response"}

    def test_set_error_raises(self):
        client = MockSplunkClientBase()
        client.set_error("/test", ValueError("Test error"))
        with pytest.raises(ValueError, match="Test error"):
            client.get("/test")

    def test_set_callback(self):
        client = MockSplunkClientBase()
        client.set_callback("/test", lambda **kwargs: {"dynamic": True})
        result = client.get("/test")
        assert result == {"dynamic": True}

    def test_clear_overrides(self):
        client = MockSplunkClientBase()
        client.set_response("/test", {"custom": "response"})
        client.set_error("/error", ValueError())
        client.clear_overrides()
        assert len(client.responses) == 0
        assert len(client.errors) == 0

    def test_clear_calls(self):
        client = MockSplunkClientBase()
        client.get("/test")
        client.post("/test")
        assert len(client.calls) == 2
        client.clear_calls()
        assert len(client.calls) == 0

    def test_get_calls_filtered_by_method(self):
        client = MockSplunkClientBase()
        client.get("/test1")
        client.post("/test2")
        client.get("/test3")
        get_calls = client.get_calls(method="GET")
        assert len(get_calls) == 2

    def test_get_calls_filtered_by_endpoint(self):
        client = MockSplunkClientBase()
        client.get("/search/jobs")
        client.get("/data/indexes")
        client.get("/search/results")
        search_calls = client.get_calls(endpoint="/search")
        assert len(search_calls) == 2

    def test_assert_called_passes(self):
        client = MockSplunkClientBase()
        client.get("/test")
        client.assert_called("GET", "/test")

    def test_assert_called_fails(self):
        client = MockSplunkClientBase()
        with pytest.raises(AssertionError):
            client.assert_called("GET", "/test")

    def test_assert_called_with_times(self):
        client = MockSplunkClientBase()
        client.get("/test")
        client.get("/test")
        client.assert_called("GET", "/test", times=2)

    def test_assert_not_called_passes(self):
        client = MockSplunkClientBase()
        client.assert_not_called("GET", "/test")

    def test_assert_not_called_fails(self):
        client = MockSplunkClientBase()
        client.get("/test")
        with pytest.raises(AssertionError):
            client.assert_not_called("GET", "/test")

    def test_get_raw_returns_bytes(self):
        client = MockSplunkClientBase()
        client.set_response("/test", b"raw bytes")
        result = client.get_raw("/test")
        assert result == b"raw bytes"

    def test_get_text_returns_string(self):
        client = MockSplunkClientBase()
        client.set_response("/test", "text response")
        result = client.get_text("/test")
        assert result == "text response"

    def test_stream_results_yields_bytes(self):
        client = MockSplunkClientBase()
        client.set_response("/test", b"chunk1")
        chunks = list(client.stream_results("/test"))
        assert chunks == [b"chunk1"]

    def test_stream_results_yields_list(self):
        client = MockSplunkClientBase()
        client.set_response("/test", [b"chunk1", b"chunk2"])
        chunks = list(client.stream_results("/test"))
        assert chunks == [b"chunk1", b"chunk2"]

    def test_stream_lines(self):
        client = MockSplunkClientBase()
        client.set_response("/test", ["line1", "line2"])
        lines = list(client.stream_lines("/test"))
        assert lines == ["line1", "line2"]

    def test_stream_json_lines(self):
        client = MockSplunkClientBase()
        client.set_response("/test", [{"a": 1}, {"b": 2}])
        items = list(client.stream_json_lines("/test"))
        assert items == [{"a": 1}, {"b": 2}]

    def test_upload_file(self):
        client = MockSplunkClientBase()
        result = client.upload_file("/upload", "/path/to/file")
        assert client.calls[0]["method"] == "UPLOAD"

    def test_upload_lookup(self):
        client = MockSplunkClientBase()
        result = client.upload_lookup("test.csv", "a,b,c\n1,2,3")
        assert result["status"] == "success"
        assert result["lookup_name"] == "test.csv"

    def test_test_connection(self):
        client = MockSplunkClientBase()
        assert client.test_connection() is True

    def test_is_cloud_false(self):
        client = MockSplunkClientBase(base_url="https://onprem.example.com")
        assert client.is_cloud is False

    def test_is_cloud_true(self):
        client = MockSplunkClientBase(base_url="https://acme.splunkcloud.com")
        assert client.is_cloud is True

    def test_repr(self):
        client = MockSplunkClientBase()
        assert "MockSplunkClientBase" in repr(client)


class TestSearchMixin:
    """Tests for SearchMixin functionality."""

    def test_oneshot_search_default_results(self):
        client = MockSearchClient()
        result = client.oneshot_search("index=main | head 10")
        assert "results" in result
        assert "fields" in result
        assert result["preview"] is False

    def test_oneshot_search_custom_results(self):
        client = MockSearchClient()
        client.set_oneshot_results([{"host": "test", "count": "5"}])
        result = client.oneshot_search("index=main | stats count")
        assert result["results"] == [{"host": "test", "count": "5"}]

    def test_search_normal_returns_sid(self):
        client = MockSearchClient()
        result = client.search_normal("index=main | head 10")
        assert "sid" in result
        assert "." in result["sid"]  # Format: timestamp.seq

    def test_search_blocking_returns_done(self):
        client = MockSearchClient()
        result = client.search_blocking("index=main | head 10")
        assert result["entry"][0]["content"]["isDone"] is True
        assert result["entry"][0]["content"]["dispatchState"] == "DONE"

    def test_get_search_results(self):
        client = MockSearchClient()
        job = client.search_normal("index=main")
        sid = job["sid"]
        results = client.get_search_results(sid)
        assert "results" in results

    def test_get_search_results_pagination(self):
        client = MockSearchClient()
        client.set_job_results("test-sid", [{"a": 1}, {"b": 2}, {"c": 3}])
        results = client.get_search_results("test-sid", count=2, offset=1)
        assert len(results["results"]) == 2
        assert results["results"][0] == {"b": 2}

    def test_get_search_preview(self):
        client = MockSearchClient()
        job = client.search_normal("index=main")
        preview = client.get_search_preview(job["sid"])
        assert preview["preview"] is True

    def test_validate_spl_valid(self):
        client = MockSearchClient()
        result = client.validate_spl("index=main | head 10")
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_spl_empty(self):
        client = MockSearchClient()
        result = client.validate_spl("")
        assert result["valid"] is False
        assert "Empty search query" in result["errors"]

    def test_validate_spl_unbalanced_quotes(self):
        client = MockSearchClient()
        result = client.validate_spl('index=main "unbalanced')
        assert result["valid"] is False
        assert "Unbalanced quotes" in result["errors"]

    def test_generate_default_results_stats(self):
        client = MockSearchClient()
        result = client.oneshot_search("index=main | stats count by host")
        # Should generate stats-like results
        assert len(result["results"]) > 0
        assert "count" in result["results"][0]

    def test_generate_default_results_timechart(self):
        client = MockSearchClient()
        result = client.oneshot_search("index=main | timechart count")
        assert "_time" in result["results"][0]


class TestJobMixin:
    """Tests for JobMixin functionality."""

    def test_create_job(self):
        client = MockJobClient()
        result = client.create_job("index=main")
        assert "sid" in result

    def test_create_job_auto_complete(self):
        client = MockJobClient()
        client.set_job_auto_complete(True)
        job = client.create_job("index=main")
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["isDone"] is True

    def test_create_job_no_auto_complete(self):
        client = MockJobClient()
        client.set_job_auto_complete(False)
        job = client.create_job("index=main")
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["isDone"] is False

    def test_get_job_status_unknown(self):
        client = MockJobClient()
        result = client.get_job_status("unknown-sid")
        assert result["entry"] == []

    def test_list_jobs(self):
        client = MockJobClient()
        client.create_job("query1")
        client.create_job("query2")
        result = client.list_jobs()
        assert len(result["entry"]) == 2

    def test_list_jobs_pagination(self):
        client = MockJobClient()
        for i in range(5):
            client.create_job(f"query{i}")
        result = client.list_jobs(count=2, offset=1)
        assert len(result["entry"]) == 2
        assert result["paging"]["total"] == 5

    def test_cancel_job(self):
        client = MockJobClient()
        client.set_job_auto_complete(False)
        job = client.create_job("index=main")
        client.cancel_job(job["sid"])
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["isDone"] is True

    def test_pause_job(self):
        client = MockJobClient()
        client.set_job_auto_complete(False)
        job = client.create_job("index=main")
        client.pause_job(job["sid"])
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["isPaused"] is True
        assert status["entry"][0]["content"]["dispatchState"] == "PAUSED"

    def test_unpause_job(self):
        client = MockJobClient()
        client.set_job_auto_complete(False)
        job = client.create_job("index=main")
        client.pause_job(job["sid"])
        client.unpause_job(job["sid"])
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["isPaused"] is False

    def test_finalize_job(self):
        client = MockJobClient()
        client.set_job_auto_complete(False)
        job = client.create_job("index=main")
        client.finalize_job(job["sid"])
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["dispatchState"] == "FINALIZING"

    def test_set_job_ttl(self):
        client = MockJobClient()
        job = client.create_job("index=main")
        client.set_job_ttl(job["sid"], 7200)
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["ttl"] == 7200

    def test_delete_job(self):
        client = MockJobClient()
        job = client.create_job("index=main")
        client.delete_job(job["sid"])
        status = client.get_job_status(job["sid"])
        assert status["entry"] == []

    def test_touch_job(self):
        client = MockJobClient()
        job = client.create_job("index=main")
        result = client.touch_job(job["sid"])
        assert result == {}

    def test_get_active_jobs(self):
        client = MockJobClient()
        client.set_job_auto_complete(False)
        client.create_job("query1")
        client.create_job("query2")
        active = client.get_active_jobs()
        assert len(active) == 2

    def test_clear_jobs(self):
        client = MockJobClient()
        client.create_job("query1")
        client.create_job("query2")
        client.clear_jobs()
        result = client.list_jobs()
        assert len(result["entry"]) == 0

    def test_set_job_state(self):
        client = MockJobClient()
        client.set_job_auto_complete(False)
        job = client.create_job("index=main")
        client.set_job_state(job["sid"], MockJobState.DONE)
        status = client.get_job_status(job["sid"])
        assert status["entry"][0]["content"]["isDone"] is True


class TestMetadataMixin:
    """Tests for MetadataMixin functionality."""

    def test_list_indexes(self):
        client = MockMetadataClient()
        result = client.list_indexes()
        assert len(result["entry"]) > 0
        # Default indexes: main, _internal, _audit
        names = [e["name"] for e in result["entry"]]
        assert "main" in names

    def test_list_indexes_with_search_filter(self):
        client = MockMetadataClient()
        result = client.list_indexes(search="main")
        assert all("main" in e["name"].lower() for e in result["entry"])

    def test_get_index_info(self):
        client = MockMetadataClient()
        result = client.get_index_info("main")
        assert result["entry"][0]["name"] == "main"
        assert "totalEventCount" in result["entry"][0]["content"]

    def test_get_index_info_unknown(self):
        client = MockMetadataClient()
        result = client.get_index_info("nonexistent")
        assert result["entry"] == []

    def test_add_index(self):
        client = MockMetadataClient()
        client.add_index("custom_index", event_count=5000)
        result = client.get_index_info("custom_index")
        assert result["entry"][0]["content"]["totalEventCount"] == 5000

    def test_list_sourcetypes(self):
        client = MockMetadataClient()
        result = client.list_sourcetypes()
        assert len(result["entry"]) > 0

    def test_list_sourcetypes_filtered_by_index(self):
        client = MockMetadataClient()
        result = client.list_sourcetypes(index="main")
        # Default sourcetypes for main: access_combined, syslog, app_logs, json
        names = [e["name"] for e in result["entry"]]
        assert "app_logs" in names

    def test_add_sourcetype(self):
        client = MockMetadataClient()
        client.add_sourcetype("main", "custom_sourcetype")
        result = client.list_sourcetypes(index="main")
        names = [e["name"] for e in result["entry"]]
        assert "custom_sourcetype" in names

    def test_list_sources(self):
        client = MockMetadataClient()
        result = client.list_sources()
        assert len(result["entry"]) > 0

    def test_add_source(self):
        client = MockMetadataClient()
        client.add_source("main", "/custom/path/log.txt")
        result = client.list_sources(index="main")
        names = [e["name"] for e in result["entry"]]
        assert "/custom/path/log.txt" in names

    def test_get_field_summary(self):
        client = MockMetadataClient()
        result = client.get_field_summary(index="main")
        assert "results" in result
        fields = [f["field"] for f in result["results"]]
        assert "_time" in fields
        assert "host" in fields

    def test_set_field_summary(self):
        client = MockMetadataClient()
        custom_fields = [{"field": "custom", "count": 100}]
        client.set_field_summary("main", None, custom_fields)
        result = client.get_field_summary(index="main")
        assert result["results"] == custom_fields

    def test_metadata_search_sourcetypes(self):
        client = MockMetadataClient()
        result = client.metadata_search(metadata_type="sourcetypes", index="main")
        assert len(result["entry"]) > 0


class TestAdminMixin:
    """Tests for AdminMixin functionality."""

    def test_get_server_info(self):
        client = MockAdminClient()
        info = client.get_server_info()
        assert "version" in info
        assert "serverName" in info

    def test_set_server_info(self):
        client = MockAdminClient()
        client.set_server_info(version="10.0.0", serverName="custom-server")
        info = client.get_server_info()
        assert info["version"] == "10.0.0"
        assert info["serverName"] == "custom-server"

    def test_get_server_health(self):
        client = MockAdminClient()
        health = client.get_server_health()
        assert health["status"] == "green"
        assert "features" in health

    def test_whoami(self):
        client = MockAdminClient()
        user = client.whoami()
        assert "username" in user
        assert "roles" in user

    def test_set_current_user(self):
        client = MockAdminClient()
        client.set_current_user(username="testuser", roles=["user"])
        user = client.whoami()
        assert user["username"] == "testuser"

    def test_list_users(self):
        client = MockAdminClient()
        result = client.list_users()
        assert len(result["entry"]) > 0
        # Default users: admin, power_user, regular_user
        names = [e["name"] for e in result["entry"]]
        assert "admin" in names

    def test_get_user(self):
        client = MockAdminClient()
        result = client.get_user("admin")
        assert result["entry"][0]["content"]["username"] == "admin"

    def test_get_user_unknown(self):
        client = MockAdminClient()
        result = client.get_user("nonexistent")
        assert result["entry"] == []

    def test_add_user(self):
        client = MockAdminClient()
        client.add_user("newuser", realname="New User", roles=["user"])
        result = client.get_user("newuser")
        assert result["entry"][0]["content"]["realname"] == "New User"

    def test_list_roles(self):
        client = MockAdminClient()
        result = client.list_roles()
        assert len(result["entry"]) > 0
        names = [e["name"] for e in result["entry"]]
        assert "admin" in names

    def test_get_role(self):
        client = MockAdminClient()
        result = client.get_role("admin")
        assert "capabilities" in result["entry"][0]["content"]

    def test_add_role(self):
        client = MockAdminClient()
        client.add_role("custom_role", capabilities=["search"])
        result = client.get_role("custom_role")
        assert "search" in result["entry"][0]["content"]["capabilities"]

    def test_get_capabilities(self):
        client = MockAdminClient()
        result = client.get_capabilities()
        assert "capabilities" in result

    def test_list_tokens(self):
        client = MockAdminClient()
        result = client.list_tokens()
        assert "entry" in result

    def test_create_token(self):
        client = MockAdminClient()
        result = client.create_token("test-token", audience="api")
        assert "token" in result["entry"][0]["content"]
        assert result["entry"][0]["content"]["name"] == "test-token"

    def test_delete_token(self):
        client = MockAdminClient()
        created = client.create_token("to-delete")
        token_id = created["entry"][0]["name"]
        client.delete_token(token_id)
        result = client.list_tokens()
        token_ids = [e["name"] for e in result["entry"]]
        assert token_id not in token_ids

    def test_rest_get(self):
        client = MockAdminClient()
        client.set_response("/custom/endpoint", {"data": "test"})
        result = client.rest_get("/custom/endpoint")
        assert result == {"data": "test"}

    def test_rest_post(self):
        client = MockAdminClient()
        client.set_response("/custom/endpoint", {"created": True})
        result = client.rest_post("/custom/endpoint", data={"name": "test"})
        assert result == {"created": True}


class TestExportMixin:
    """Tests for ExportMixin functionality."""

    def test_export_results_csv(self):
        client = MockExportClient()
        client.set_export_data("test-sid", [
            {"host": "server1", "count": "10"},
            {"host": "server2", "count": "20"},
        ])
        chunks = list(client.export_results("test-sid", output_mode="csv"))
        data = b"".join(chunks).decode("utf-8")
        assert "host" in data
        assert "server1" in data

    def test_export_results_json(self):
        client = MockExportClient()
        client.set_export_data("test-sid", [{"host": "server1"}])
        chunks = list(client.export_results("test-sid", output_mode="json"))
        data = b"".join(chunks).decode("utf-8")
        assert "results" in data

    def test_export_results_json_rows(self):
        client = MockExportClient()
        client.set_export_data("test-sid", [{"a": 1}, {"b": 2}])
        chunks = list(client.export_results("test-sid", output_mode="json_rows"))
        data = b"".join(chunks).decode("utf-8")
        lines = data.strip().split("\n")
        assert len(lines) == 2

    def test_export_results_pagination(self):
        client = MockExportClient()
        client.set_export_data("test-sid", [{"i": i} for i in range(10)])
        chunks = list(client.export_results("test-sid", count=3, offset=2))
        # Should only include items 2, 3, 4

    def test_export_results_to_file(self):
        client = MockExportClient()
        client.set_export_data("test-sid", [{"a": 1}])
        result = client.export_results_to_file("test-sid", "/tmp/out.csv")
        assert result["status"] == "success"
        assert result["output_file"] == "/tmp/out.csv"

    def test_stream_export(self):
        client = MockExportClient()
        chunks = list(client.stream_export("index=main | head 10"))
        assert len(chunks) > 0

    def test_stream_json_lines(self):
        client = MockExportClient()
        client.set_export_data("test-sid", [{"a": 1}, {"b": 2}])
        items = list(client.stream_json_lines("test-sid"))
        assert len(items) == 2

    def test_set_export_chunk_size(self):
        client = MockExportClient()
        client.set_export_chunk_size(10)
        # Chunk size affects internal chunking


class TestMockSplunkClient:
    """Tests for the full MockSplunkClient."""

    def test_has_all_mixins(self):
        client = MockSplunkClient()
        # Search
        assert hasattr(client, "oneshot_search")
        # Job
        assert hasattr(client, "create_job")
        # Metadata
        assert hasattr(client, "list_indexes")
        # Admin
        assert hasattr(client, "get_server_info")
        # Export
        assert hasattr(client, "export_results")

    def test_reset_clears_all_state(self):
        client = MockSplunkClient()
        client.get("/test")
        client.create_job("query")
        client.oneshot_search("query")
        client.reset()
        assert len(client.calls) == 0
        assert len(client._jobs) == 0


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_mock_client(self):
        client = create_mock_client()
        assert isinstance(client, MockSplunkClient)

    def test_create_mock_client_with_overrides(self):
        client = create_mock_client(port=9999)
        assert client.port == 9999

    def test_create_cloud_mock(self):
        client = create_cloud_mock()
        assert client.is_cloud is True

    def test_create_minimal_mock_search_only(self):
        client = create_minimal_mock(search=True)
        assert hasattr(client, "oneshot_search")
        assert not hasattr(client, "create_job")

    def test_create_minimal_mock_multiple(self):
        client = create_minimal_mock(search=True, job=True)
        assert hasattr(client, "oneshot_search")
        assert hasattr(client, "create_job")


class TestResponseFactory:
    """Tests for ResponseFactory."""

    def test_paginated(self):
        items = [{"name": f"item{i}"} for i in range(10)]
        result = ResponseFactory.paginated(items, start_at=2, max_results=3)
        assert len(result["entry"]) == 3
        assert result["paging"]["total"] == 10
        assert result["paging"]["offset"] == 2

    def test_search_results(self):
        results = [{"host": "a", "count": "1"}, {"host": "b", "count": "2"}]
        response = ResponseFactory.search_results(results)
        assert response["preview"] is False
        assert len(response["fields"]) == 2  # host, count

    def test_job_entry(self):
        response = ResponseFactory.job_entry("test-sid", result_count=50)
        assert response["entry"][0]["name"] == "test-sid"
        assert response["entry"][0]["content"]["resultCount"] == 50

    def test_error_response(self):
        response = ResponseFactory.error_response("Something failed", code=500)
        assert response["messages"][0]["text"] == "Something failed"
        assert response["messages"][0]["code"] == 500

    def test_empty_response(self):
        response = ResponseFactory.empty_response()
        assert response["entry"] == []


class TestJobFactory:
    """Tests for JobFactory."""

    def test_running(self):
        response = JobFactory.running(progress=0.7)
        content = response["entry"][0]["content"]
        assert content["dispatchState"] == "RUNNING"
        assert content["isDone"] is False

    def test_done(self):
        response = JobFactory.done(result_count=100)
        content = response["entry"][0]["content"]
        assert content["dispatchState"] == "DONE"
        assert content["isDone"] is True
        assert content["resultCount"] == 100

    def test_failed(self):
        response = JobFactory.failed(error_message="Query syntax error")
        content = response["entry"][0]["content"]
        assert content["dispatchState"] == "FAILED"
        assert content["isFailed"] is True


class TestIndexFactory:
    """Tests for IndexFactory."""

    def test_index_entry(self):
        entry = IndexFactory.index_entry("test_index", event_count=5000)
        assert entry["name"] == "test_index"
        assert entry["totalEventCount"] == 5000

    def test_index_list(self):
        response = IndexFactory.index_list(["main", "test"])
        assert len(response["entry"]) == 2


class TestUserFactory:
    """Tests for UserFactory."""

    def test_user_entry(self):
        user = UserFactory.user_entry("testuser", roles=["admin"])
        assert user["username"] == "testuser"
        assert "admin" in user["roles"]

    def test_admin_user(self):
        user = UserFactory.admin_user()
        assert user["username"] == "admin"
        assert "admin" in user["roles"]


class TestTimestampFactory:
    """Tests for TimestampFactory."""

    def test_now(self):
        ts = TimestampFactory.now()
        assert isinstance(ts, str)
        assert "T" in ts  # ISO format

    def test_epoch(self):
        ts = TimestampFactory.epoch()
        assert isinstance(ts, float)

    def test_formatted(self):
        ts = TimestampFactory.formatted(2024, 6, 15, 14, 30, 0)
        assert ts == "2024-06-15T14:30:00"


class TestResultFactory:
    """Tests for ResultFactory."""

    def test_log_event(self):
        event = ResultFactory.log_event("Test message", host="server1")
        assert event["_raw"] == "Test message"
        assert event["host"] == "server1"

    def test_stats_row(self):
        row = ResultFactory.stats_row(host="server1", count=100)
        assert row["host"] == "server1"
        assert row["count"] == "100"  # Converted to string

    def test_timechart_row(self):
        row = ResultFactory.timechart_row("2024-01-01T12:00:00", count=50)
        assert row["_time"] == "2024-01-01T12:00:00"
        assert row["count"] == "50"

    def test_sample_results(self):
        results = ResultFactory.sample_results(count=5)
        assert len(results) == 5
        assert all("_raw" in r for r in results)


class TestSkillSpecificClients:
    """Tests for skill-specific mock clients."""

    def test_mock_search_client(self):
        client = MockSearchClient()
        result = client.oneshot_search("index=main")
        assert "results" in result

    def test_mock_job_client(self):
        client = MockJobClient()
        job = client.create_job("index=main")
        assert "sid" in job

    def test_mock_metadata_client(self):
        client = MockMetadataClient()
        indexes = client.list_indexes()
        assert "entry" in indexes

    def test_mock_admin_client(self):
        client = MockAdminClient()
        info = client.get_server_info()
        assert "version" in info

    def test_mock_export_client(self):
        client = MockExportClient()
        chunks = list(client.stream_export("index=main"))
        assert len(chunks) > 0


class TestCombinationClients:
    """Tests for combination mock clients."""

    def test_mock_search_job_client(self):
        client = MockSearchJobClient()
        # Has search
        result = client.oneshot_search("index=main")
        assert "results" in result
        # Has job
        job = client.create_job("index=main")
        assert "sid" in job

    def test_mock_search_export_client(self):
        client = MockSearchExportClient()
        # Has search
        job = client.search_normal("index=main")
        # Has export
        chunks = list(client.export_results(job["sid"]))
        assert len(chunks) > 0

    def test_mock_full_search_client(self):
        client = MockFullSearchClient()
        # Has search, job, export, metadata
        assert hasattr(client, "oneshot_search")
        assert hasattr(client, "create_job")
        assert hasattr(client, "export_results")
        assert hasattr(client, "list_indexes")
