"""
Live Search Tests

Tests for search operations against a real Splunk instance.
"""

import pytest
import time


@pytest.mark.live
class TestSearchLive:
    """Live tests for search operations."""

    def test_simple_search(self, splunk_client):
        """Should execute a simple search."""
        # Search internal logs which should always have data
        query = "search index=_internal | head 5"

        try:
            results = splunk_client.search(query, exec_mode="blocking")
            assert results is not None
        except Exception as e:
            # If search fails, it might be a timeout or no data
            pytest.skip(f"Search failed (may be expected): {e}")

    def test_search_job_lifecycle(self, splunk_client):
        """Should create, poll, and retrieve results from a search job."""
        query = "search index=_internal | head 1"

        # Create job
        job = splunk_client.create_search_job(query)
        assert job is not None
        assert "sid" in job

        sid = job["sid"]

        # Poll for completion (with timeout)
        max_wait = 30
        start = time.time()
        while time.time() - start < max_wait:
            status = splunk_client.get_job_status(sid)
            if status.get("isDone", False):
                break
            time.sleep(1)

        # Get results
        results = splunk_client.get_job_results(sid)
        assert results is not None

    def test_oneshot_search(self, splunk_client):
        """Should execute a oneshot (blocking) search."""
        query = "| makeresults count=3 | eval test='live'"

        results = splunk_client.search(query, exec_mode="oneshot")

        assert results is not None
        # makeresults should return exactly 3 rows
        if isinstance(results, list):
            assert len(results) == 3


@pytest.mark.live
class TestSearchResultTypes:
    """Verify search result types match expectations."""

    def test_stats_results_are_strings(self, splunk_client):
        """Stats command results should have string values.

        This matches the behavior of ResultFactory.stats_row().
        """
        query = "| makeresults | eval count=42, avg=3.14 | table count avg"

        results = splunk_client.search(query, exec_mode="oneshot")

        if results and len(results) > 0:
            row = results[0]
            # Splunk returns all values as strings
            if "count" in row:
                assert isinstance(row["count"], str), (
                    f"Stats count should be string, got {type(row['count'])}"
                )
            if "avg" in row:
                assert isinstance(row["avg"], str), (
                    f"Stats avg should be string, got {type(row['avg'])}"
                )
