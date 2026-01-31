"""
Search Mixin for Mock Splunk Client

Provides mock responses for search-related operations:
- Oneshot searches
- Normal/blocking searches
- Search results
- SPL validation
"""

import time
import uuid
from typing import Any, Dict, List, Optional


class SearchMixin:
    """Mixin providing search-related mock methods.

    Add to MockSplunkClientBase to enable search operation mocking.
    Maintains internal state for search jobs and results.

    Example:
        class MyMock(SearchMixin, MockSplunkClientBase):
            pass

        client = MyMock()
        result = client.oneshot_search("index=main | head 10")
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize search mixin state."""
        super().__init__(*args, **kwargs)
        self._search_results: Dict[str, List[Dict[str, Any]]] = {}
        self._oneshot_results: List[Dict[str, Any]] = []

    def set_oneshot_results(self, results: List[Dict[str, Any]]) -> None:
        """Set results to return for oneshot searches.

        Args:
            results: List of result dictionaries
        """
        self._oneshot_results = results

    def set_job_results(self, sid: str, results: List[Dict[str, Any]]) -> None:
        """Set results for a specific job SID.

        Args:
            sid: Search job ID
            results: List of result dictionaries
        """
        self._search_results[sid] = results

    def oneshot_search(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        max_count: int = 50000,
        output_mode: str = "json",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute mock oneshot search.

        Args:
            spl: SPL query string
            earliest_time: Search start time
            latest_time: Search end time
            max_count: Maximum results
            output_mode: Output format

        Returns:
            Search results with preview, fields, and results
        """
        self._record_call(
            "POST",
            "/services/search/jobs/oneshot",
            data={
                "search": spl,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "max_count": max_count,
                "output_mode": output_mode,
            },
        )

        # Return configured or default results
        results = self._oneshot_results or self._generate_default_results(spl)

        return {
            "preview": False,
            "init_offset": 0,
            "fields": self._extract_fields(results),
            "results": results,
        }

    def search_normal(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create mock normal (async) search job.

        Args:
            spl: SPL query string
            earliest_time: Search start time
            latest_time: Search end time

        Returns:
            Dict with sid
        """
        sid = self._generate_sid()

        self._record_call(
            "POST",
            "/services/search/v2/jobs",
            data={
                "search": spl,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "exec_mode": "normal",
            },
        )

        # Store default results for this job
        if sid not in self._search_results:
            self._search_results[sid] = self._generate_default_results(spl)

        return {"sid": sid}

    def search_blocking(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        timeout: int = 300,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create mock blocking search job.

        Args:
            spl: SPL query string
            earliest_time: Search start time
            latest_time: Search end time
            timeout: Search timeout

        Returns:
            Dict with entry containing job info
        """
        sid = self._generate_sid()

        self._record_call(
            "POST",
            "/services/search/v2/jobs",
            data={
                "search": spl,
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "exec_mode": "blocking",
            },
            timeout=timeout,
        )

        if sid not in self._search_results:
            self._search_results[sid] = self._generate_default_results(spl)

        return {
            "entry": [
                {
                    "name": sid,
                    "content": {
                        "sid": sid,
                        "dispatchState": "DONE",
                        "isDone": True,
                        "resultCount": len(self._search_results.get(sid, [])),
                    },
                }
            ]
        }

    def get_search_results(
        self,
        sid: str,
        count: int = 50000,
        offset: int = 0,
        output_mode: str = "json",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get results from completed search job.

        Args:
            sid: Search job ID
            count: Maximum results to return
            offset: Result offset
            output_mode: Output format

        Returns:
            Search results
        """
        endpoint = f"/services/search/v2/jobs/{sid}/results"

        self._record_call(
            "GET",
            endpoint,
            params={"count": count, "offset": offset, "output_mode": output_mode},
        )

        results = self._search_results.get(sid, [])

        # Apply pagination
        paginated = results[offset : offset + count]

        return {
            "preview": False,
            "init_offset": offset,
            "fields": self._extract_fields(paginated),
            "results": paginated,
        }

    def get_search_preview(
        self,
        sid: str,
        count: int = 100,
        offset: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get preview results from running search job.

        Args:
            sid: Search job ID
            count: Maximum results
            offset: Result offset

        Returns:
            Preview results
        """
        endpoint = f"/services/search/v2/jobs/{sid}/results_preview"

        self._record_call(
            "GET",
            endpoint,
            params={"count": count, "offset": offset},
        )

        results = self._search_results.get(sid, [])
        # Return subset for preview
        preview = results[: min(count, 10)]

        return {
            "preview": True,
            "init_offset": 0,
            "fields": self._extract_fields(preview),
            "results": preview,
        }

    def validate_spl(self, spl: str) -> Dict[str, Any]:
        """Validate SPL syntax.

        Args:
            spl: SPL query to validate

        Returns:
            Validation result with valid flag and any errors
        """
        self._record_call(
            "POST",
            "/services/search/parser",
            data={"q": spl, "parse_only": True},
        )

        # Simple validation - check for common issues
        errors = []
        if not spl.strip():
            errors.append("Empty search query")
        if spl.count('"') % 2 != 0:
            errors.append("Unbalanced quotes")
        if spl.count("[") != spl.count("]"):
            errors.append("Unbalanced brackets")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def _generate_sid(self) -> str:
        """Generate a realistic search job ID."""
        timestamp = int(time.time())
        seq = uuid.uuid4().hex[:5]
        return f"{timestamp}.{seq}"

    def _generate_default_results(self, spl: str) -> List[Dict[str, Any]]:
        """Generate default search results based on SPL.

        Args:
            spl: SPL query

        Returns:
            List of mock result dictionaries
        """
        # Parse for stats command to generate appropriate results
        if "stats count" in spl.lower():
            return [
                {"host": "server1", "count": "150"},
                {"host": "server2", "count": "120"},
                {"host": "server3", "count": "80"},
            ]
        elif "timechart" in spl.lower():
            return [
                {"_time": "2024-01-01T00:00:00", "count": "100"},
                {"_time": "2024-01-01T01:00:00", "count": "125"},
                {"_time": "2024-01-01T02:00:00", "count": "110"},
            ]
        else:
            return [
                {
                    "_time": "2024-01-01T12:00:00",
                    "_raw": "Sample log event 1",
                    "host": "server1",
                    "source": "/var/log/app.log",
                    "sourcetype": "app_logs",
                },
                {
                    "_time": "2024-01-01T12:00:01",
                    "_raw": "Sample log event 2",
                    "host": "server2",
                    "source": "/var/log/app.log",
                    "sourcetype": "app_logs",
                },
            ]

    def _extract_fields(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract field metadata from results.

        Args:
            results: List of result dictionaries

        Returns:
            List of field definitions
        """
        if not results:
            return []

        fields: set[str] = set()
        for result in results:
            fields.update(result.keys())

        return [{"name": f} for f in sorted(fields)]

    def _record_call(self, *args: Any, **kwargs: Any) -> None:
        """Record call - delegates to base class."""
        # This will be provided by MockSplunkClientBase
        if hasattr(super(), "_record_call"):
            super()._record_call(*args, **kwargs)  # type: ignore[misc]
