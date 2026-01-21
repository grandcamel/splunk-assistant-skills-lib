"""
Protocol Definitions for Mock Splunk Client

Defines the interface contract that mixins expect from the base class.
Used for static type checking without runtime overhead.
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Protocol,
    runtime_checkable,
)


@runtime_checkable
class MockClientProtocol(Protocol):
    """Protocol defining the contract mixins expect from the base class.

    This protocol documents what methods and attributes the base class
    must provide for mixins to function correctly.

    Usage in mixins:
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from ..protocols import MockClientProtocol
            _Base = MockClientProtocol
        else:
            _Base = object

        class MyMixin(_Base):
            # Type hints work, no runtime overhead
            pass
    """

    # Instance attributes
    base_url: str
    port: int
    timeout: int
    auth_method: str
    calls: List[Dict[str, Any]]
    responses: Dict[str, Any]
    errors: Dict[str, Exception]

    # Core HTTP methods
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "GET request",
    ) -> Dict[str, Any]:
        """Execute mock GET request."""
        ...

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "POST request",
    ) -> Dict[str, Any]:
        """Execute mock POST request."""
        ...

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "PUT request",
    ) -> Dict[str, Any]:
        """Execute mock PUT request."""
        ...

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "DELETE request",
    ) -> Dict[str, Any]:
        """Execute mock DELETE request."""
        ...

    # Streaming methods
    def stream_results(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        chunk_size: int = 8192,
        timeout: Optional[int] = None,
        operation: str = "stream results",
    ) -> Generator[bytes, None, None]:
        """Stream results as bytes."""
        ...

    def stream_lines(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "stream lines",
    ) -> Iterator[str]:
        """Stream results as lines."""
        ...

    def stream_json_lines(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "stream JSON lines",
    ) -> Iterator[Dict[str, Any]]:
        """Stream results as JSON objects."""
        ...

    # Call tracking
    def _record_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Record an API call."""
        ...

    def _get_response(
        self,
        endpoint: str,
        default: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get response for endpoint."""
        ...

    # Override management
    def set_response(self, endpoint: str, response: Any) -> None:
        """Set static response for endpoint."""
        ...

    def set_callback(self, endpoint: str, callback: Callable[..., Any]) -> None:
        """Set dynamic callback for endpoint."""
        ...

    def set_error(self, endpoint: str, error: Exception) -> None:
        """Set error to raise for endpoint."""
        ...

    def clear_overrides(self) -> None:
        """Clear all response overrides."""
        ...

    def clear_calls(self) -> None:
        """Clear recorded calls."""
        ...

    # Assertions
    def assert_called(
        self,
        method: str,
        endpoint: str,
        times: Optional[int] = None,
    ) -> None:
        """Assert endpoint was called."""
        ...

    def assert_not_called(self, method: str, endpoint: str) -> None:
        """Assert endpoint was not called."""
        ...

    # Context manager
    def close(self) -> None:
        """Close the client."""
        ...

    def __enter__(self) -> "MockClientProtocol":
        """Enter context."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context."""
        ...


class SearchMixinProtocol(Protocol):
    """Protocol for search-related functionality.

    Defines what the SearchMixin provides beyond the base class.
    """

    _search_results: Dict[str, List[Dict[str, Any]]]
    _oneshot_results: List[Dict[str, Any]]

    def set_oneshot_results(self, results: List[Dict[str, Any]]) -> None:
        """Set oneshot search results."""
        ...

    def set_job_results(self, sid: str, results: List[Dict[str, Any]]) -> None:
        """Set results for a job."""
        ...

    def oneshot_search(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        max_count: int = 50000,
        output_mode: str = "json",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute oneshot search."""
        ...

    def search_normal(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create normal search job."""
        ...

    def search_blocking(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        timeout: int = 300,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create blocking search job."""
        ...

    def get_search_results(
        self,
        sid: str,
        count: int = 50000,
        offset: int = 0,
        output_mode: str = "json",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get search results."""
        ...


class JobMixinProtocol(Protocol):
    """Protocol for job-related functionality.

    Defines what the JobMixin provides beyond the base class.
    """

    _jobs: Dict[str, Dict[str, Any]]

    def create_job(
        self,
        spl: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        exec_mode: str = "normal",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a search job."""
        ...

    def get_job_status(self, sid: str) -> Dict[str, Any]:
        """Get job status."""
        ...

    def list_jobs(
        self,
        count: int = 30,
        offset: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List jobs."""
        ...

    def cancel_job(self, sid: str) -> Dict[str, Any]:
        """Cancel a job."""
        ...

    def pause_job(self, sid: str) -> Dict[str, Any]:
        """Pause a job."""
        ...

    def unpause_job(self, sid: str) -> Dict[str, Any]:
        """Resume a job."""
        ...

    def delete_job(self, sid: str) -> Dict[str, Any]:
        """Delete a job."""
        ...

    def clear_jobs(self) -> None:
        """Clear all jobs."""
        ...


class MetadataMixinProtocol(Protocol):
    """Protocol for metadata-related functionality."""

    _indexes: Dict[str, Dict[str, Any]]
    _sourcetypes: Dict[str, List[str]]
    _sources: Dict[str, List[str]]

    def list_indexes(
        self,
        count: int = 30,
        offset: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List indexes."""
        ...

    def get_index_info(self, index_name: str) -> Dict[str, Any]:
        """Get index information."""
        ...

    def list_sourcetypes(
        self,
        index: Optional[str] = None,
        count: int = 100,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List sourcetypes."""
        ...


class AdminMixinProtocol(Protocol):
    """Protocol for admin-related functionality."""

    _server_info: Dict[str, Any]
    _current_user: Dict[str, Any]
    _users: Dict[str, Dict[str, Any]]
    _roles: Dict[str, Dict[str, Any]]

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        ...

    def whoami(self) -> Dict[str, Any]:
        """Get current user."""
        ...

    def list_users(
        self,
        count: int = 30,
        offset: int = 0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List users."""
        ...


class ExportMixinProtocol(Protocol):
    """Protocol for export-related functionality."""

    _export_data: Dict[str, List[Dict[str, Any]]]

    def export_results(
        self,
        sid: str,
        output_mode: str = "csv",
        count: int = 0,
        offset: int = 0,
        **kwargs: Any,
    ) -> Generator[bytes, None, None]:
        """Export results as stream."""
        ...

    def stream_json_lines(
        self,
        sid: str,
        count: int = 0,
        offset: int = 0,
        **kwargs: Any,
    ) -> Iterator[Dict[str, Any]]:
        """Stream results as JSON objects."""
        ...
