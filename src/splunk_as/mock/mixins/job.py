"""
Job Mixin for Mock Splunk Client

Provides mock responses for search job lifecycle operations:
- Job creation and status
- Job control (pause, cancel, finalize)
- Job listing and deletion
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional


class MockJobState(str, Enum):
    """Mock job dispatch states."""

    QUEUED = "QUEUED"
    PARSING = "PARSING"
    RUNNING = "RUNNING"
    FINALIZING = "FINALIZING"
    DONE = "DONE"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


class JobMixin:
    """Mixin providing job lifecycle mock methods.

    Maintains internal state for job tracking and progression.

    Example:
        class MyMock(JobMixin, MockSplunkClientBase):
            pass

        client = MyMock()
        job = client.create_job("index=main | head 10")
        status = client.get_job_status(job["sid"])
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize job mixin state."""
        super().__init__(*args, **kwargs)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._job_auto_complete = True
        self._job_completion_delay = 0.0

    def set_job_auto_complete(self, auto_complete: bool) -> None:
        """Configure whether jobs auto-complete.

        Args:
            auto_complete: If True, jobs complete immediately
        """
        self._job_auto_complete = auto_complete

    def set_job_state(self, sid: str, state: str | MockJobState) -> None:
        """Manually set a job's state.

        Args:
            sid: Job ID
            state: New state
        """
        if sid in self._jobs:
            self._jobs[sid]["dispatchState"] = (
                state.value if isinstance(state, MockJobState) else state
            )
            if state in (MockJobState.DONE, "DONE"):
                self._jobs[sid]["isDone"] = True
                self._jobs[sid]["doneProgress"] = 1.0
            elif state in (MockJobState.FAILED, "FAILED"):
                self._jobs[sid]["isDone"] = True
                self._jobs[sid]["isFailed"] = True

    def create_job(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        exec_mode: str = "normal",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a mock search job.

        Args:
            spl: SPL query
            earliest_time: Search start time
            latest_time: Search end time
            exec_mode: Execution mode (normal/blocking)

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
                "exec_mode": exec_mode,
            },
        )

        # Initialize job state
        initial_state = (
            MockJobState.DONE if self._job_auto_complete else MockJobState.RUNNING
        )

        self._jobs[sid] = {
            "sid": sid,
            "search": spl,
            "dispatchState": initial_state.value,
            "doneProgress": 1.0 if self._job_auto_complete else 0.5,
            "eventCount": 1000,
            "resultCount": 100,
            "scanCount": 5000,
            "runDuration": 2.5,
            "isDone": self._job_auto_complete,
            "isFailed": False,
            "isPaused": False,
            "ttl": 600,
            "createTime": time.time(),
        }

        return {"sid": sid}

    def get_job_status(self, sid: str) -> Dict[str, Any]:
        """Get job status.

        Args:
            sid: Job ID

        Returns:
            Job status information
        """
        endpoint = f"/services/search/v2/jobs/{sid}"

        self._record_call("GET", endpoint)

        job = self._jobs.get(sid)
        if not job:
            # Return empty response for unknown jobs
            return {"entry": []}

        return {
            "entry": [
                {
                    "name": sid,
                    "content": job,
                }
            ]
        }

    def list_jobs(
        self,
        count: int = 30,
        offset: int = 0,
        sort_key: str = "createTime",
        sort_dir: str = "desc",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List search jobs.

        Args:
            count: Maximum jobs to return
            offset: Offset for pagination
            sort_key: Sort field
            sort_dir: Sort direction

        Returns:
            List of jobs
        """
        self._record_call(
            "GET",
            "/services/search/jobs",
            params={
                "count": count,
                "offset": offset,
                "sort_key": sort_key,
                "sort_dir": sort_dir,
            },
        )

        # Sort jobs
        jobs = list(self._jobs.values())
        reverse = sort_dir == "desc"
        jobs.sort(key=lambda j: j.get(sort_key, 0), reverse=reverse)

        # Paginate
        paginated = jobs[offset : offset + count]

        return {
            "entry": [{"name": j["sid"], "content": j} for j in paginated],
            "paging": {
                "total": len(self._jobs),
                "offset": offset,
                "count": len(paginated),
            },
        }

    def cancel_job(self, sid: str) -> Dict[str, Any]:
        """Cancel a running job.

        Args:
            sid: Job ID

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/search/v2/jobs/{sid}/control"

        self._record_call("POST", endpoint, data={"action": "cancel"})

        if sid in self._jobs:
            self._jobs[sid]["dispatchState"] = MockJobState.DONE.value
            self._jobs[sid]["isDone"] = True

        return {}

    def pause_job(self, sid: str) -> Dict[str, Any]:
        """Pause a running job.

        Args:
            sid: Job ID

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/search/v2/jobs/{sid}/control"

        self._record_call("POST", endpoint, data={"action": "pause"})

        if sid in self._jobs:
            self._jobs[sid]["dispatchState"] = MockJobState.PAUSED.value
            self._jobs[sid]["isPaused"] = True

        return {}

    def unpause_job(self, sid: str) -> Dict[str, Any]:
        """Resume a paused job.

        Args:
            sid: Job ID

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/search/v2/jobs/{sid}/control"

        self._record_call("POST", endpoint, data={"action": "unpause"})

        if sid in self._jobs:
            self._jobs[sid]["dispatchState"] = MockJobState.RUNNING.value
            self._jobs[sid]["isPaused"] = False

        return {}

    def finalize_job(self, sid: str) -> Dict[str, Any]:
        """Finalize a running job (stop and return current results).

        Args:
            sid: Job ID

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/search/v2/jobs/{sid}/control"

        self._record_call("POST", endpoint, data={"action": "finalize"})

        if sid in self._jobs:
            self._jobs[sid]["dispatchState"] = MockJobState.FINALIZING.value

        return {}

    def set_job_ttl(self, sid: str, ttl: int) -> Dict[str, Any]:
        """Set job time-to-live.

        Args:
            sid: Job ID
            ttl: Time-to-live in seconds

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/search/v2/jobs/{sid}/control"

        self._record_call("POST", endpoint, data={"action": "setttl", "ttl": ttl})

        if sid in self._jobs:
            self._jobs[sid]["ttl"] = ttl

        return {}

    def delete_job(self, sid: str) -> Dict[str, Any]:
        """Delete a job.

        Args:
            sid: Job ID

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/search/jobs/{sid}"

        self._record_call("DELETE", endpoint)

        if sid in self._jobs:
            del self._jobs[sid]

        return {}

    def touch_job(self, sid: str) -> Dict[str, Any]:
        """Touch a job to extend its TTL.

        Args:
            sid: Job ID

        Returns:
            Empty dict on success
        """
        endpoint = f"/services/search/v2/jobs/{sid}/control"

        self._record_call("POST", endpoint, data={"action": "touch"})

        return {}

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of currently active (not done) jobs.

        Returns:
            List of active job dictionaries
        """
        return [j for j in self._jobs.values() if not j.get("isDone", False)]

    def clear_jobs(self) -> None:
        """Clear all tracked jobs."""
        self._jobs.clear()

    def _generate_sid(self) -> str:
        """Generate a realistic search job ID."""
        timestamp = int(time.time())
        seq = uuid.uuid4().hex[:5]
        return f"{timestamp}.{seq}"

    def _record_call(self, *args: Any, **kwargs: Any) -> None:
        """Record call - delegates to base class."""
        if hasattr(super(), "_record_call"):
            super()._record_call(*args, **kwargs)  # type: ignore[misc]
