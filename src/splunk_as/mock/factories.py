"""
Response Factories for Mock Splunk Client

Provides factory classes for building consistent API response structures.
Use these factories when setting up custom mock responses.
"""

import time
import uuid
from typing import Any, Dict, List, Optional


class ResponseFactory:
    """Factory for building Splunk API responses."""

    @staticmethod
    def paginated(
        items: List[Any],
        start_at: int = 0,
        max_results: int = 30,
        name_field: str = "name",
    ) -> Dict[str, Any]:
        """Build a paginated response.

        Args:
            items: List of items to paginate
            start_at: Starting offset
            max_results: Maximum items per page
            name_field: Field to use as entry name

        Returns:
            Paginated response dict with entry and paging
        """
        total = len(items)
        page = items[start_at : start_at + max_results]

        entries = []
        for item in page:
            if isinstance(item, dict):
                name = item.get(name_field, str(uuid.uuid4()))
                entries.append({"name": name, "content": item})
            else:
                entries.append({"name": str(item), "content": {"value": item}})

        return {
            "entry": entries,
            "paging": {
                "total": total,
                "offset": start_at,
                "count": len(page),
                "perPage": max_results,
            },
        }

    @staticmethod
    def search_results(
        results: List[Dict[str, Any]],
        preview: bool = False,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Build a search results response.

        Args:
            results: List of result dictionaries
            preview: Whether these are preview results
            offset: Starting offset

        Returns:
            Search results response
        """
        # Extract field names from results
        fields: set[str] = set()
        for result in results:
            fields.update(result.keys())

        return {
            "preview": preview,
            "init_offset": offset,
            "fields": [{"name": f} for f in sorted(fields)],
            "results": results,
        }

    @staticmethod
    def job_entry(
        sid: str,
        dispatch_state: str = "DONE",
        is_done: bool = True,
        result_count: int = 100,
        event_count: int = 1000,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build a job entry response.

        Args:
            sid: Search job ID
            dispatch_state: Job state
            is_done: Whether job is complete
            result_count: Number of results
            event_count: Number of events
            **kwargs: Additional job properties

        Returns:
            Job entry response
        """
        content = {
            "sid": sid,
            "dispatchState": dispatch_state,
            "isDone": is_done,
            "isFailed": False,
            "isPaused": False,
            "resultCount": result_count,
            "eventCount": event_count,
            "scanCount": event_count * 5,
            "doneProgress": 1.0 if is_done else 0.5,
            "runDuration": 2.5,
            "ttl": 600,
            **kwargs,
        }

        return {
            "entry": [{"name": sid, "content": content}],
        }

    @staticmethod
    def error_response(
        message: str,
        code: int = 400,
        error_type: str = "FATAL",
    ) -> Dict[str, Any]:
        """Build an error response.

        Args:
            message: Error message
            code: HTTP status code
            error_type: Error type (FATAL, WARN, INFO)

        Returns:
            Error response dict
        """
        return {
            "messages": [
                {
                    "type": error_type,
                    "text": message,
                    "code": code,
                }
            ]
        }

    @staticmethod
    def empty_response() -> Dict[str, Any]:
        """Build an empty response.

        Returns:
            Empty entry list response
        """
        return {"entry": []}


class JobFactory:
    """Factory for building job-related responses."""

    @staticmethod
    def running(
        sid: Optional[str] = None,
        progress: float = 0.5,
        event_count: int = 500,
    ) -> Dict[str, Any]:
        """Build a running job response.

        Args:
            sid: Job ID (generated if not provided)
            progress: Progress percentage (0-1)
            event_count: Events processed so far

        Returns:
            Running job response
        """
        if sid is None:
            sid = f"{int(time.time())}.{uuid.uuid4().hex[:5]}"

        return ResponseFactory.job_entry(
            sid=sid,
            dispatch_state="RUNNING",
            is_done=False,
            result_count=0,
            event_count=event_count,
            doneProgress=progress,
        )

    @staticmethod
    def done(
        sid: Optional[str] = None,
        result_count: int = 100,
        event_count: int = 1000,
    ) -> Dict[str, Any]:
        """Build a completed job response.

        Args:
            sid: Job ID (generated if not provided)
            result_count: Final result count
            event_count: Total events processed

        Returns:
            Completed job response
        """
        if sid is None:
            sid = f"{int(time.time())}.{uuid.uuid4().hex[:5]}"

        return ResponseFactory.job_entry(
            sid=sid,
            dispatch_state="DONE",
            is_done=True,
            result_count=result_count,
            event_count=event_count,
        )

    @staticmethod
    def failed(
        sid: Optional[str] = None,
        error_message: str = "Search failed",
    ) -> Dict[str, Any]:
        """Build a failed job response.

        Args:
            sid: Job ID (generated if not provided)
            error_message: Failure message

        Returns:
            Failed job response
        """
        if sid is None:
            sid = f"{int(time.time())}.{uuid.uuid4().hex[:5]}"

        return ResponseFactory.job_entry(
            sid=sid,
            dispatch_state="FAILED",
            is_done=True,
            result_count=0,
            event_count=0,
            isFailed=True,
            messages=[{"type": "FATAL", "text": error_message}],
        )


class IndexFactory:
    """Factory for building index-related responses."""

    @staticmethod
    def index_entry(
        name: str,
        event_count: int = 100000,
        size_mb: int = 1024,
        disabled: bool = False,
    ) -> Dict[str, Any]:
        """Build an index entry.

        Args:
            name: Index name
            event_count: Total events
            size_mb: Size in MB
            disabled: Whether disabled

        Returns:
            Index entry dict
        """
        return {
            "name": name,
            "totalEventCount": event_count,
            "currentDBSizeMB": size_mb,
            "maxDataSizeMB": 500000,
            "disabled": disabled,
            "minTime": "2024-01-01T00:00:00",
            "maxTime": "2024-01-15T23:59:59",
        }

    @staticmethod
    def index_list(
        indexes: List[str],
        event_counts: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Build an index list response.

        Args:
            indexes: List of index names
            event_counts: Optional event counts per index

        Returns:
            Index list response
        """
        entries = []
        for i, name in enumerate(indexes):
            count = event_counts[i] if event_counts and i < len(event_counts) else 100000
            entries.append({
                "name": name,
                "content": IndexFactory.index_entry(name, event_count=count),
            })

        return {
            "entry": entries,
            "paging": {"total": len(indexes), "offset": 0, "count": len(indexes)},
        }


class UserFactory:
    """Factory for building user-related responses."""

    @staticmethod
    def user_entry(
        username: str,
        realname: Optional[str] = None,
        roles: Optional[List[str]] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a user entry.

        Args:
            username: Username
            realname: Display name
            roles: List of roles
            email: Email address

        Returns:
            User entry dict
        """
        return {
            "username": username,
            "realname": realname or username.title(),
            "email": email or f"{username}@example.com",
            "roles": roles or ["user"],
            "capabilities": ["search"],
            "defaultApp": "search",
        }

    @staticmethod
    def admin_user() -> Dict[str, Any]:
        """Build an admin user entry.

        Returns:
            Admin user dict
        """
        return UserFactory.user_entry(
            username="admin",
            realname="Administrator",
            roles=["admin", "power", "user"],
            email="admin@example.com",
        )


class TimestampFactory:
    """Factory for building timestamp values."""

    @staticmethod
    def now() -> str:
        """Get current timestamp in Splunk format.

        Returns:
            ISO timestamp string
        """
        return time.strftime("%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def epoch() -> float:
        """Get current Unix timestamp.

        Returns:
            Unix timestamp
        """
        return time.time()

    @staticmethod
    def formatted(
        year: int = 2024,
        month: int = 1,
        day: int = 1,
        hour: int = 12,
        minute: int = 0,
        second: int = 0,
    ) -> str:
        """Build a formatted timestamp.

        Args:
            year: Year
            month: Month (1-12)
            day: Day (1-31)
            hour: Hour (0-23)
            minute: Minute (0-59)
            second: Second (0-59)

        Returns:
            Formatted timestamp string
        """
        return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"


class ResultFactory:
    """Factory for building search result entries."""

    @staticmethod
    def log_event(
        message: str,
        host: str = "server1",
        source: str = "/var/log/app.log",
        sourcetype: str = "app_logs",
        index: str = "main",
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a log event result.

        Args:
            message: Log message (_raw)
            host: Host name
            source: Source path
            sourcetype: Sourcetype
            index: Index name
            timestamp: Event time

        Returns:
            Log event dict
        """
        return {
            "_time": timestamp or TimestampFactory.now(),
            "_raw": message,
            "host": host,
            "source": source,
            "sourcetype": sourcetype,
            "index": index,
        }

    @staticmethod
    def stats_row(**kwargs: Any) -> Dict[str, Any]:
        """Build a stats result row.

        Args:
            **kwargs: Field name/value pairs

        Returns:
            Stats row dict
        """
        return {k: str(v) for k, v in kwargs.items()}

    @staticmethod
    def timechart_row(
        timestamp: str,
        **values: Any,
    ) -> Dict[str, Any]:
        """Build a timechart result row.

        Args:
            timestamp: _time value
            **values: Metric values

        Returns:
            Timechart row dict
        """
        return {
            "_time": timestamp,
            "_span": "3600",
            **{k: str(v) for k, v in values.items()},
        }

    @staticmethod
    def sample_results(count: int = 10) -> List[Dict[str, Any]]:
        """Generate sample log results.

        Args:
            count: Number of results

        Returns:
            List of log event dicts
        """
        results = []
        for i in range(count):
            results.append(
                ResultFactory.log_event(
                    message=f"Sample log event {i + 1}",
                    host=f"server{(i % 5) + 1}",
                    timestamp=TimestampFactory.formatted(
                        hour=12, minute=i % 60, second=i
                    ),
                )
            )
        return results
