#!/usr/bin/env python3
"""
Splunk REST API HTTP Client

Provides a robust HTTP client for interacting with the Splunk REST API.
Supports both JWT Bearer token and Basic Auth authentication.
Includes automatic retry with exponential backoff for transient failures.

Features:
    - Dual authentication: JWT Bearer token (preferred) or Basic Auth
    - Automatic retry on 429/5xx errors with exponential backoff
    - Configurable timeouts for short and long-running operations
    - SSL verification with option to disable for self-signed certs
    - Content negotiation (JSON by default)
    - Streaming support for large result sets
"""

from __future__ import annotations

import csv
import io
import json
import re
import time
from typing import Any, Dict, Generator, Iterator, List, Optional, Union, cast

import requests

from .error_handler import handle_splunk_error
from .validators import validate_file_path


class SplunkClient:
    """HTTP client for Splunk REST API with retry logic and dual auth support."""

    DEFAULT_PORT = 8089
    DEFAULT_TIMEOUT = 30
    DEFAULT_SEARCH_TIMEOUT = 300
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2.0
    RETRY_STATUS_CODES = [429, 500, 502, 503, 504]

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        port: int = DEFAULT_PORT,
        timeout: int = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
        max_retries: int = MAX_RETRIES,
        retry_backoff: float = RETRY_BACKOFF,
    ):
        """
        Initialize Splunk client.

        Args:
            base_url: Splunk host URL (e.g., https://splunk.example.com)
            token: JWT Bearer token for authentication (preferred)
            username: Username for Basic Auth (alternative to token)
            password: Password for Basic Auth (alternative to token)
            port: Management port (default: 8089)
            timeout: Request timeout in seconds (default: 30)
            verify_ssl: Verify SSL certificates (default: True)
            max_retries: Maximum retry attempts (default: 3)
            retry_backoff: Exponential backoff multiplier (default: 2.0)

        Raises:
            ValueError: If neither token nor username+password provided
        """
        # Normalize base URL
        base_url = base_url.rstrip("/")
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"

        self.base_url = f"{base_url}:{port}/services"
        self.port = port
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff

        # Create session
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        )

        # Configure authentication
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
            self.auth_method = "bearer"
        elif username and password:
            self.session.auth = (username, password)
            self.auth_method = "basic"
        else:
            raise ValueError("Must provide either token or username+password")

    def close(self) -> None:
        """Close the session and release resources.

        This method should be called when you're done using the client
        to ensure proper cleanup of HTTP connections. Alternatively,
        use the client as a context manager with `with` statement.

        Example:
            >>> client = SplunkClient(base_url="...", token="...")
            >>> try:
            ...     result = client.get("/server/info")
            ... finally:
            ...     client.close()
        """
        if self.session:
            self.session.close()

    def __enter__(self) -> "SplunkClient":
        """Context manager entry.

        Example:
            >>> with SplunkClient(base_url="...", token="...") as client:
            ...     result = client.get("/server/info")
            ... # Session automatically closed on exit
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit - close session.

        The session is closed regardless of whether an exception occurred.
        """
        self.close()

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint path."""
        endpoint = endpoint.lstrip("/")
        if not endpoint.startswith("services"):
            return f"{self.base_url}/{endpoint}"
        # Handle full path starting with services
        base = self.base_url.rsplit("/services", 1)[0]
        return f"{base}/{endpoint}"

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        stream: bool = False,
        operation: str = "API request",
        raw_response: bool = False,
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: URL query parameters
            data: Form data for POST/PUT
            json_body: JSON body for POST/PUT
            timeout: Override default timeout
            stream: Enable streaming response
            operation: Description for error messages
            raw_response: If True, don't add default output_mode=json

        Returns:
            Response object

        Raises:
            SplunkError: On API errors after retries exhausted
        """
        url = self._build_url(endpoint)
        request_timeout = timeout or self.timeout

        # Only add output_mode=json if not already specified and not a raw request
        if params is None:
            params = {}
        if not raw_response and "output_mode" not in params:
            params["output_mode"] = "json"

        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json_body,
                    timeout=request_timeout,
                    verify=self.verify_ssl,
                    stream=stream,
                )

                # Check for errors
                if response.status_code >= 400:
                    # Retry on specific status codes if retries remain
                    if (
                        response.status_code in self.RETRY_STATUS_CODES
                        and attempt < self.max_retries
                    ):
                        wait_time = self.retry_backoff**attempt
                        time.sleep(wait_time)
                        continue
                    # Handle error (non-retryable or retries exhausted)
                    handle_splunk_error(response, operation)

                return response

            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = self.retry_backoff**attempt
                    time.sleep(wait_time)
                    continue
                raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state in _request")

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "GET request",
    ) -> Dict[str, Any]:
        """
        Make GET request and return JSON response.

        Args:
            endpoint: API endpoint path
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        response = self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
            timeout=timeout,
            operation=operation,
        )
        return cast(Dict[str, Any], response.json())

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "POST request",
    ) -> Dict[str, Any]:
        """
        Make POST request and return JSON response.

        Args:
            endpoint: API endpoint path
            data: Form data
            params: URL query parameters
            json_body: JSON body (alternative to form data)
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        response = self._request(
            method="POST",
            endpoint=endpoint,
            data=data,
            json_body=json_body,
            params=params,
            timeout=timeout,
            operation=operation,
        )
        return cast(Dict[str, Any], response.json())

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "PUT request",
    ) -> Dict[str, Any]:
        """
        Make PUT request and return JSON response.

        Args:
            endpoint: API endpoint path
            data: Form data
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        response = self._request(
            method="PUT",
            endpoint=endpoint,
            data=data,
            params=params,
            timeout=timeout,
            operation=operation,
        )
        return cast(Dict[str, Any], response.json())

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "DELETE request",
    ) -> Dict[str, Any]:
        """
        Make DELETE request and return JSON response.

        Args:
            endpoint: API endpoint path
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Parsed JSON response
        """
        response = self._request(
            method="DELETE",
            endpoint=endpoint,
            params=params,
            timeout=timeout,
            operation=operation,
        )
        return cast(Dict[str, Any], response.json())

    def get_raw(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "GET raw request",
    ) -> bytes:
        """
        Make GET request and return raw response bytes.

        Use this for endpoints that return non-JSON data (CSV, XML, raw text).

        Args:
            endpoint: API endpoint path
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Raw response content as bytes
        """
        response = self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
            timeout=timeout,
            operation=operation,
            raw_response=True,
        )
        return response.content

    def get_text(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "GET text request",
    ) -> str:
        """
        Make GET request and return response as text.

        Use this for endpoints that return non-JSON text data (CSV, XML).

        Args:
            endpoint: API endpoint path
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Response content as string
        """
        response = self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
            timeout=timeout,
            operation=operation,
            raw_response=True,
        )
        return response.text

    def post_raw(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "POST raw request",
    ) -> bytes:
        """
        Make POST request and return raw response bytes.

        Use this for endpoints that return non-JSON data (CSV, XML, raw text).

        Args:
            endpoint: API endpoint path
            data: Form data
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Raw response content as bytes
        """
        response = self._request(
            method="POST",
            endpoint=endpoint,
            data=data,
            params=params,
            timeout=timeout,
            operation=operation,
            raw_response=True,
        )
        return response.content

    def post_text(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "POST text request",
    ) -> str:
        """
        Make POST request and return response as text.

        Use this for endpoints that return non-JSON text data (CSV, XML).

        Args:
            endpoint: API endpoint path
            data: Form data
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Response content as string
        """
        response = self._request(
            method="POST",
            endpoint=endpoint,
            data=data,
            params=params,
            timeout=timeout,
            operation=operation,
            raw_response=True,
        )
        return response.text

    def upload_file(
        self,
        endpoint: str,
        file_path: str,
        file_field: str = "datafile",
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "file upload",
    ) -> Dict[str, Any]:
        """
        Upload file to Splunk.

        Args:
            endpoint: API endpoint path
            file_path: Path to file to upload
            file_field: Form field name for file (default: datafile)
            data: Additional form data
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Parsed JSON response

        Raises:
            ValidationError: If file path contains traversal attempts
        """
        # Validate file path to prevent directory traversal
        file_path = validate_file_path(file_path, "file_path")

        url = self._build_url(endpoint)
        request_timeout = timeout or self.timeout

        # Remove Content-Type header for multipart
        headers = dict(self.session.headers)
        headers.pop("Content-Type", None)

        with open(file_path, "rb") as f:
            files = {file_field: f}
            response = self.session.post(
                url=url,
                files=files,
                data=data or {},
                params={"output_mode": "json"},
                timeout=request_timeout,
                verify=self.verify_ssl,
                headers=headers,
            )

        if response.status_code >= 400:
            handle_splunk_error(response, operation)

        return cast(Dict[str, Any], response.json())

    @staticmethod
    def _escape_spl_value(value: str) -> str:
        """Escape a value for safe use in SPL eval statements.

        Prevents SPL injection by properly escaping special characters.

        Args:
            value: Raw string value

        Returns:
            Escaped string safe for use in SPL double-quoted strings
        """
        # Escape backslashes first, then double quotes
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _validate_lookup_name(lookup_name: str) -> str:
        """Validate and sanitize lookup name to prevent command injection.

        Args:
            lookup_name: Proposed lookup file name

        Returns:
            Sanitized lookup name

        Raises:
            ValueError: If lookup name contains invalid characters
        """
        # Only allow alphanumeric, underscore, hyphen, and dot
        if not re.match(r"^[\w\-\.]+$", lookup_name):
            raise ValueError(
                f"Invalid lookup name '{lookup_name}': "
                "only alphanumeric, underscore, hyphen, and dot allowed"
            )
        return lookup_name

    @staticmethod
    def _validate_spl_field_name(field_name: str) -> str:
        """Validate field name for safe use in SPL statements.

        Prevents SPL injection via malicious CSV header names.
        Splunk field names must start with a letter or underscore
        and contain only alphanumeric characters and underscores.

        Args:
            field_name: CSV header or field name to validate

        Returns:
            Validated field name

        Raises:
            ValueError: If field name contains invalid characters
        """
        # Must start with letter or underscore, contain only alphanumeric and underscore
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", field_name):
            raise ValueError(
                f"Invalid field name '{field_name}': "
                "must start with letter or underscore, "
                "contain only alphanumeric and underscore"
            )
        return field_name

    def upload_lookup(
        self,
        lookup_name: str,
        content: Union[str, bytes],
        app: str = "search",
        namespace: str = "nobody",
        timeout: Optional[int] = None,
        operation: str = "upload lookup",
    ) -> Dict[str, Any]:
        """
        Upload a lookup table file to Splunk using outputlookup.

        This method creates a lookup file by using the SPL outputlookup command
        via a search job. This approach works for both on-prem and Splunk Cloud.

        Args:
            lookup_name: Name for the lookup file (will add .csv if missing)
            content: CSV content as string or bytes (first row must be headers)
            app: App namespace (default: search)
            namespace: User namespace (default: nobody)
            timeout: Override default timeout
            operation: Description for error messages

        Returns:
            Dict with status info including:
            - status: "success"
            - lookup_name: final lookup filename
            - rows_uploaded: number of rows successfully processed
            - rows_total: total data rows in input (excluding header)
            - warning: (optional) message if rows were skipped
            - skipped_rows: (optional) list of skipped row numbers

        Example:
            >>> csv_content = "user,email\\njohn,john@example.com"
            >>> client.upload_lookup("users", csv_content)
        """
        # Ensure lookup name has .csv extension and validate
        if not lookup_name.endswith(".csv"):
            lookup_name = f"{lookup_name}.csv"
        lookup_name = self._validate_lookup_name(lookup_name)

        # Convert bytes to string if needed
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        # Parse CSV content using proper CSV parser
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)

        if len(rows) < 2:
            raise ValueError(
                "CSV content must have at least a header row and one data row"
            )

        headers = rows[0]
        data_rows = rows[1:]

        # Validate all header names to prevent SPL injection
        for header in headers:
            self._validate_spl_field_name(header)

        # Build SPL to create events from CSV rows and output to lookup
        # Use makeresults with append to build multiple rows
        spl_parts: List[str] = []
        successful_rows = 0
        skipped_rows: List[int] = []

        for i, values in enumerate(data_rows):
            row_num = i + 2  # 1-indexed, accounting for header

            if len(values) != len(headers):
                skipped_rows.append(row_num)
                continue

            # Build eval statements with proper escaping
            evals = ", ".join(
                f'{h}="{self._escape_spl_value(v)}"' for h, v in zip(headers, values)
            )

            if successful_rows == 0:
                spl_parts.append(f"| makeresults | eval {evals}")
            else:
                spl_parts.append(f"| append [| makeresults | eval {evals}]")

            successful_rows += 1

        if successful_rows == 0:
            raise ValueError("No valid rows to upload after parsing CSV")

        # Add outputlookup (quote name for defense-in-depth)
        spl = " ".join(spl_parts) + f' | outputlookup "{lookup_name}"'

        request_timeout = timeout or self.DEFAULT_SEARCH_TIMEOUT

        # Run as oneshot search
        self.post(
            f"/servicesNS/{namespace}/{app}/search/jobs/oneshot",
            data={
                "search": spl,
                "output_mode": "json",
            },
            timeout=request_timeout,
            operation=operation,
        )

        result: Dict[str, Any] = {
            "status": "success",
            "lookup_name": lookup_name,
            "rows_uploaded": successful_rows,
            "rows_total": len(data_rows),
        }

        if skipped_rows:
            result["warning"] = f"Skipped {len(skipped_rows)} malformed rows"
            result["skipped_rows"] = skipped_rows

        return result

    def stream_results(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        chunk_size: int = 8192,
        timeout: Optional[int] = None,
        operation: str = "stream results",
    ) -> Generator[bytes, None, None]:
        """
        Stream results from endpoint.

        Args:
            endpoint: API endpoint path
            params: URL query parameters
            chunk_size: Size of chunks to yield
            timeout: Override default timeout
            operation: Description for error messages

        Yields:
            Chunks of response data
        """
        response = self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
            timeout=timeout or self.DEFAULT_SEARCH_TIMEOUT,
            stream=True,
            operation=operation,
        )

        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk

    def stream_lines(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "stream lines",
    ) -> Iterator[str]:
        """
        Stream results line by line.

        Args:
            endpoint: API endpoint path
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Yields:
            Lines of response data
        """
        response = self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
            timeout=timeout or self.DEFAULT_SEARCH_TIMEOUT,
            stream=True,
            operation=operation,
        )

        for line in response.iter_lines(decode_unicode=True):
            if line:
                yield line

    def stream_json_lines(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation: str = "stream JSON lines",
    ) -> Iterator[Dict[str, Any]]:
        """
        Stream results as parsed JSON objects, one per line.

        Splunk export endpoints return JSON Lines format (NDJSON) where
        each line is a separate JSON object. This method parses each line.

        Args:
            endpoint: API endpoint path
            params: URL query parameters
            timeout: Override default timeout
            operation: Description for error messages

        Yields:
            Parsed JSON objects from each line

        Example:
            >>> for record in client.stream_json_lines("/export", {"search": "..."}):
            ...     print(record)
        """
        # Ensure output_mode is json for JSON lines
        if params is None:
            params = {}
        if "output_mode" not in params:
            params["output_mode"] = "json"

        response = self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
            timeout=timeout or self.DEFAULT_SEARCH_TIMEOUT,
            stream=True,
            operation=operation,
            raw_response=True,  # Don't override output_mode
        )

        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # Skip non-JSON lines (e.g., empty or malformed)
                    continue

    def get_server_info(self) -> Dict[str, Any]:
        """Get Splunk server information."""
        response = self.get("/server/info", operation="get server info")
        if "entry" in response and response["entry"]:
            return cast(Dict[str, Any], response["entry"][0].get("content", {}))
        return response

    def whoami(self) -> Dict[str, Any]:
        """Get current user information."""
        response = self.get("/authentication/current-context", operation="whoami")
        if "entry" in response and response["entry"]:
            return cast(Dict[str, Any], response["entry"][0].get("content", {}))
        return response

    def test_connection(self) -> bool:
        """
        Test connection to Splunk.

        Returns:
            True if connection successful

        Raises:
            SplunkError: If connection fails
        """
        self.get_server_info()
        return True

    @property
    def is_cloud(self) -> bool:
        """Check if connected to Splunk Cloud."""
        return ".splunkcloud.com" in self.base_url

    def __repr__(self) -> str:
        return f"SplunkClient(base_url={self.base_url!r}, auth_method={self.auth_method!r})"
