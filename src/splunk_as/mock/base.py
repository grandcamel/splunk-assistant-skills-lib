"""
Base Mock Splunk Client

Provides the foundational mock client class that other mixins extend.
Simulates the core HTTP methods (get, post, put, delete) and tracks
all API calls for verification in tests.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, cast


def is_mock_mode() -> bool:
    """Check if Splunk mock mode is enabled.

    Returns:
        True if SPLUNK_MOCK_MODE environment variable is set to 'true'.
    """
    return os.environ.get("SPLUNK_MOCK_MODE", "").lower() == "true"


class MockSplunkClientBase:
    """Base mock implementation of SplunkClient.

    Provides core functionality shared by all mixins:
    - Request/response simulation
    - Call tracking for verification
    - Configurable response overrides
    - Error simulation

    Attributes:
        base_url: Simulated Splunk base URL
        auth_method: Authentication method (bearer/basic)
        timeout: Default request timeout
        calls: List of recorded API calls for verification
        responses: Dict of endpoint -> response overrides
        errors: Dict of endpoint -> error to raise
    """

    DEFAULT_PORT = 8089
    DEFAULT_TIMEOUT = 30
    DEFAULT_SEARCH_TIMEOUT = 300

    def __init__(
        self,
        base_url: str = "https://mock-splunk.example.com",
        token: Optional[str] = "mock-token",
        username: Optional[str] = None,
        password: Optional[str] = None,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
        max_retries: int = 3,
        retry_backoff: float = 2.0,
    ):
        """Initialize mock client.

        Args:
            base_url: Simulated Splunk host URL
            token: JWT Bearer token (default: mock-token)
            username: Username for Basic Auth
            password: Password for Basic Auth
            port: Management port (default: 8089)
            timeout: Request timeout in seconds
            verify_ssl: SSL verification flag (ignored in mock)
            max_retries: Retry attempts (ignored in mock)
            retry_backoff: Backoff multiplier (ignored in mock)
        """
        self.base_url = f"{base_url.rstrip('/')}:{port}/services"
        self.port = port
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Authentication
        if token:
            self.auth_method = "bearer"
            self._token = token
        elif username and password:
            self.auth_method = "basic"
            self._username = username
            self._password = password
        else:
            self.auth_method = "bearer"
            self._token = "mock-token"

        # Call tracking
        self.calls: List[Dict[str, Any]] = []

        # Response overrides
        self.responses: Dict[str, Any] = {}

        # Error simulation
        self.errors: Dict[str, Exception] = {}

        # Callbacks for dynamic responses
        self._callbacks: Dict[str, Callable[..., Any]] = {}

    def close(self) -> None:
        """Close mock client (no-op for mock)."""
        pass

    def __enter__(self) -> "MockSplunkClientBase":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.close()

    def _record_call(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Record an API call for later verification."""
        self.calls.append(
            {
                "method": method,
                "endpoint": endpoint,
                "params": params,
                "data": data,
                "timestamp": time.time(),
                **kwargs,
            }
        )

    def _get_response(
        self,
        endpoint: str,
        default: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get response for endpoint, checking overrides first."""
        # Check for error simulation
        if endpoint in self.errors:
            raise self.errors[endpoint]

        # Check for callback
        if endpoint in self._callbacks:
            return cast(Dict[str, Any], self._callbacks[endpoint](**kwargs))

        # Check for static override
        if endpoint in self.responses:
            return cast(Dict[str, Any], self.responses[endpoint])

        # Return default
        return default or {"entry": []}

    def set_response(self, endpoint: str, response: Any) -> None:
        """Set a static response for an endpoint.

        Args:
            endpoint: API endpoint path
            response: Response to return for this endpoint
        """
        self.responses[endpoint] = response

    def set_callback(self, endpoint: str, callback: Callable[..., Any]) -> None:
        """Set a callback for dynamic response generation.

        Args:
            endpoint: API endpoint path
            callback: Function that returns response
        """
        self._callbacks[endpoint] = callback

    def set_error(self, endpoint: str, error: Exception) -> None:
        """Set an error to raise for an endpoint.

        Args:
            endpoint: API endpoint path
            error: Exception to raise
        """
        self.errors[endpoint] = error

    def clear_overrides(self) -> None:
        """Clear all response overrides, errors, and callbacks."""
        self.responses.clear()
        self.errors.clear()
        self._callbacks.clear()

    def clear_calls(self) -> None:
        """Clear recorded API calls."""
        self.calls.clear()

    def get_calls(
        self,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recorded calls, optionally filtered.

        Args:
            method: Filter by HTTP method
            endpoint: Filter by endpoint (substring match)

        Returns:
            List of matching call records
        """
        result = self.calls
        if method:
            result = [c for c in result if c["method"] == method]
        if endpoint:
            result = [c for c in result if endpoint in c["endpoint"]]
        return result

    def assert_called(
        self,
        method: str,
        endpoint: str,
        times: Optional[int] = None,
    ) -> None:
        """Assert an endpoint was called.

        Args:
            method: HTTP method
            endpoint: Endpoint path (substring match)
            times: Expected call count (None = at least once)

        Raises:
            AssertionError: If assertion fails
        """
        matching = self.get_calls(method=method, endpoint=endpoint)
        if times is not None:
            assert len(matching) == times, (
                f"Expected {endpoint} to be called {times} times, "
                f"was called {len(matching)} times"
            )
        else:
            assert len(matching) > 0, f"Expected {endpoint} to be called at least once"

    def assert_not_called(self, method: str, endpoint: str) -> None:
        """Assert an endpoint was never called.

        Args:
            method: HTTP method
            endpoint: Endpoint path (substring match)

        Raises:
            AssertionError: If endpoint was called
        """
        matching = self.get_calls(method=method, endpoint=endpoint)
        assert len(matching) == 0, (
            f"Expected {endpoint} to not be called, "
            f"was called {len(matching)} times"
        )

    # Core HTTP methods

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "GET request",
    ) -> Dict[str, Any]:
        """Mock GET request."""
        self._record_call("GET", endpoint, params=params, timeout=timeout)
        return self._get_response(endpoint, params=params)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "POST request",
    ) -> Dict[str, Any]:
        """Mock POST request."""
        self._record_call("POST", endpoint, params=params, data=data, timeout=timeout)
        return self._get_response(endpoint, data=data, params=params)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "PUT request",
    ) -> Dict[str, Any]:
        """Mock PUT request."""
        self._record_call("PUT", endpoint, params=params, data=data, timeout=timeout)
        return self._get_response(endpoint, data=data, params=params)

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "DELETE request",
    ) -> Dict[str, Any]:
        """Mock DELETE request."""
        self._record_call("DELETE", endpoint, params=params, timeout=timeout)
        return self._get_response(endpoint, params=params)

    def get_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "GET raw request",
    ) -> bytes:
        """Mock raw GET request."""
        self._record_call("GET_RAW", endpoint, params=params, timeout=timeout)
        response = self._get_response(endpoint, params=params)
        if isinstance(response, bytes):
            return response
        return b""

    def get_text(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "GET text request",
    ) -> str:
        """Mock text GET request."""
        self._record_call("GET_TEXT", endpoint, params=params, timeout=timeout)
        response = self._get_response(endpoint, params=params)
        if isinstance(response, str):
            return response
        return ""

    def post_raw(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "POST raw request",
    ) -> bytes:
        """Mock raw POST request."""
        self._record_call(
            "POST_RAW", endpoint, params=params, data=data, timeout=timeout
        )
        response = self._get_response(endpoint, data=data, params=params)
        if isinstance(response, bytes):
            return response
        return b""

    def post_text(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "POST text request",
    ) -> str:
        """Mock text POST request."""
        self._record_call(
            "POST_TEXT", endpoint, params=params, data=data, timeout=timeout
        )
        response = self._get_response(endpoint, data=data, params=params)
        if isinstance(response, str):
            return response
        return ""

    def stream_results(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        chunk_size: int = 8192,
        timeout: Optional[int] = None,
        operation: str = "stream results",
    ) -> Generator[bytes, None, None]:
        """Mock streaming results."""
        self._record_call("STREAM", endpoint, params=params, timeout=timeout)
        response = self._get_response(endpoint, params=params)
        if isinstance(response, bytes):
            yield response
        elif isinstance(response, list):
            for chunk in response:
                yield chunk if isinstance(chunk, bytes) else str(chunk).encode()

    def stream_lines(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "stream lines",
    ) -> Iterator[str]:
        """Mock streaming lines."""
        self._record_call("STREAM_LINES", endpoint, params=params, timeout=timeout)
        response = self._get_response(endpoint, params=params)
        if isinstance(response, list):
            for line in response:
                yield str(line)

    def stream_json_lines(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "stream JSON lines",
    ) -> Iterator[Dict[str, Any]]:
        """Mock streaming JSON lines."""
        self._record_call("STREAM_JSON", endpoint, params=params, timeout=timeout)
        response = self._get_response(endpoint, params=params)
        if isinstance(response, list):
            for item in response:
                if isinstance(item, dict):
                    yield item

    def upload_file(
        self,
        endpoint: str,
        file_path: str,
        file_field: str = "datafile",
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "file upload",
    ) -> Dict[str, Any]:
        """Mock file upload."""
        self._record_call(
            "UPLOAD", endpoint, data=data, file_path=file_path, timeout=timeout
        )
        return self._get_response(endpoint, data=data)

    def upload_lookup(
        self,
        lookup_name: str,
        content: str | bytes,
        app: str = "search",
        namespace: str = "nobody",
        timeout: Optional[int] = None,
        operation: str = "upload lookup",
    ) -> Dict[str, Any]:
        """Mock lookup upload."""
        endpoint = (
            f"/servicesNS/{namespace}/{app}/data/lookup-table-files/{lookup_name}"
        )
        self._record_call(
            "UPLOAD_LOOKUP",
            endpoint,
            data={"lookup_name": lookup_name, "content": content[:100]},
            timeout=timeout,
        )
        return {
            "status": "success",
            "lookup_name": lookup_name,
            "rows_uploaded": 10,
            "rows_total": 10,
        }

    def test_connection(self) -> bool:
        """Mock connection test (always succeeds)."""
        self._record_call("GET", "/server/info")
        return True

    @property
    def is_cloud(self) -> bool:
        """Check if mock is configured as Splunk Cloud."""
        return ".splunkcloud.com" in self.base_url

    def __repr__(self) -> str:
        return f"MockSplunkClientBase(base_url={self.base_url!r})"
