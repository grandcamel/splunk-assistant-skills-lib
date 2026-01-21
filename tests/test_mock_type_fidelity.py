"""
Mock Type Fidelity Tests

Verifies that mock factories return data types matching the real Splunk API.
This prevents type mismatch bugs where tests pass with mocks but fail with real API.
"""

import pytest
from splunk_as.mock.factories import (
    IndexFactory,
    JobFactory,
    ResponseFactory,
    ResultFactory,
    UserFactory,
)


class TestIndexFactoryTypeFidelity:
    """Test that IndexFactory returns correct types matching real Splunk API."""

    def test_index_entry_returns_string_types(self):
        """totalEventCount and currentDBSizeMB must be strings (real API behavior)."""
        entry = IndexFactory.index_entry("main", event_count=1000, size_mb=512)

        # These fields are strings in the real API
        assert isinstance(entry["totalEventCount"], str), (
            "totalEventCount must be string - real Splunk API returns strings"
        )
        assert isinstance(entry["currentDBSizeMB"], str), (
            "currentDBSizeMB must be string - real Splunk API returns strings"
        )
        assert isinstance(entry["maxDataSizeMB"], str), (
            "maxDataSizeMB must be string - real Splunk API returns strings"
        )

    def test_index_entry_disabled_is_lowercase_string(self):
        """disabled field must be 'true' or 'false' string (not bool)."""
        enabled_entry = IndexFactory.index_entry("main", disabled=False)
        disabled_entry = IndexFactory.index_entry("disabled_idx", disabled=True)

        assert enabled_entry["disabled"] == "false", (
            "disabled=False should produce 'false' string"
        )
        assert disabled_entry["disabled"] == "true", (
            "disabled=True should produce 'true' string"
        )

    def test_index_entry_values_are_correct(self):
        """Verify string values match the input numbers."""
        entry = IndexFactory.index_entry("test", event_count=42, size_mb=100)

        assert entry["totalEventCount"] == "42"
        assert entry["currentDBSizeMB"] == "100"
        assert entry["name"] == "test"

    def test_index_list_entries_have_string_types(self):
        """Verify index_list produces entries with string types."""
        result = IndexFactory.index_list(["main", "summary"], event_counts=[1000, 2000])

        for entry in result["entry"]:
            content = entry["content"]
            assert isinstance(content["totalEventCount"], str), (
                f"Index {entry['name']}: totalEventCount must be string"
            )
            assert isinstance(content["currentDBSizeMB"], str), (
                f"Index {entry['name']}: currentDBSizeMB must be string"
            )


class TestResultFactoryTypeFidelity:
    """Test that ResultFactory returns correct types."""

    def test_stats_row_returns_strings(self):
        """stats_row should convert all values to strings."""
        row = ResultFactory.stats_row(count=100, avg=3.14, name="test")

        assert isinstance(row["count"], str)
        assert isinstance(row["avg"], str)
        assert isinstance(row["name"], str)
        assert row["count"] == "100"
        assert row["avg"] == "3.14"

    def test_timechart_row_values_are_strings(self):
        """timechart_row should convert metric values to strings."""
        row = ResultFactory.timechart_row("2024-01-01T00:00:00", requests=500, errors=5)

        assert isinstance(row["requests"], str)
        assert isinstance(row["errors"], str)
        assert row["_span"] == "3600"


class TestJobFactoryTypeFidelity:
    """Test that JobFactory returns expected types."""

    def test_job_entry_numeric_fields_are_correct_types(self):
        """Job entry numeric fields should match API types."""
        result = ResponseFactory.job_entry(
            sid="12345.1",
            dispatch_state="DONE",
            is_done=True,
            result_count=100,
            event_count=1000,
        )

        content = result["entry"][0]["content"]
        # These are booleans in the API
        assert isinstance(content["isDone"], bool)
        assert isinstance(content["isFailed"], bool)
        # These are integers in the API
        assert isinstance(content["resultCount"], int)
        assert isinstance(content["eventCount"], int)
        # This is a float
        assert isinstance(content["doneProgress"], float)


class TestPaginationTypeFidelity:
    """Test that pagination responses have correct types."""

    def test_paginated_paging_fields_are_integers(self):
        """Paging fields (total, offset, count, perPage) should be integers."""
        result = ResponseFactory.paginated(
            items=[{"name": "item1"}, {"name": "item2"}],
            start_at=0,
            max_results=10,
        )

        paging = result["paging"]
        assert isinstance(paging["total"], int)
        assert isinstance(paging["offset"], int)
        assert isinstance(paging["count"], int)
        assert isinstance(paging["perPage"], int)
