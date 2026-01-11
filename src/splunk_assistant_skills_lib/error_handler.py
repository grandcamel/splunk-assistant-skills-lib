#!/usr/bin/env python3
"""
Splunk Error Handling

Provides a comprehensive exception hierarchy and error handling utilities
for Splunk REST API interactions.
"""

import functools
import json
import sys
from typing import Any, Callable, Dict, Optional

import requests
from assistant_skills_lib.error_handler import (
    AuthenticationError as BaseAuthenticationError,
)
from assistant_skills_lib.error_handler import (
    BaseAPIError,
)
from assistant_skills_lib.error_handler import NotFoundError as BaseNotFoundError
from assistant_skills_lib.error_handler import PermissionError as BasePermissionError
from assistant_skills_lib.error_handler import RateLimitError as BaseRateLimitError
from assistant_skills_lib.error_handler import ServerError as BaseServerError
from assistant_skills_lib.error_handler import ValidationError as BaseValidationError
from assistant_skills_lib.error_handler import handle_errors as base_handle_errors
from assistant_skills_lib.error_handler import print_error as base_print_error
from assistant_skills_lib.error_handler import (
    sanitize_error_message as base_sanitize_error_message,
)


class SplunkError(BaseAPIError):
    """Base exception for all Splunk-related errors."""

    pass


class AuthenticationError(BaseAuthenticationError, SplunkError):
    """Raised when authentication fails (401 Unauthorized)."""

    def __init__(
        self,
        message: str = "Authentication failed. Check your token or credentials.",
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)


class AuthorizationError(BasePermissionError, SplunkError):
    """Raised when user lacks required permissions (403 Forbidden)."""

    def __init__(
        self,
        message: str = "Insufficient permissions to perform this operation.",
        capability: Optional[str] = None,
        **kwargs: Any,
    ):
        self.capability = capability
        if capability:
            message = f"{message} Required capability: {capability}"
        super().__init__(message, **kwargs)


class ValidationError(BaseValidationError, SplunkError):
    """Raised for invalid input or request parameters (400 Bad Request)."""

    def __init__(
        self,
        message: str = "Invalid request parameters.",
        field: Optional[str] = None,
        **kwargs: Any,
    ):
        self.field = field
        if field:
            message = f"Invalid value for '{field}': {message}"
        super().__init__(message, **kwargs)


class NotFoundError(BaseNotFoundError, SplunkError):
    """Raised when requested resource is not found (404 Not Found)."""

    def __init__(
        self,
        message: str = "Resource not found.",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ):
        if resource_type and resource_id:
            message = f"{resource_type} '{resource_id}' not found."
        elif resource_type:
            message = f"{resource_type} not found."
        super().__init__(message, **kwargs)


class RateLimitError(BaseRateLimitError, SplunkError):
    """Raised when rate limit is exceeded (429 Too Many Requests)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Too many concurrent searches.",
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)


class ServerError(BaseServerError, SplunkError):
    """Raised for server-side errors (5xx)."""

    def __init__(self, message: str = "Splunk server error.", **kwargs: Any):
        super().__init__(message, **kwargs)


class SearchQuotaError(ServerError):
    """Raised when search quota is exhausted (503 Service Unavailable)."""

    def __init__(
        self,
        message: str = "Search quota exhausted. No available search slots.",
        **kwargs: Any,
    ):
        super().__init__(message, status_code=503, **kwargs)


class JobFailedError(SplunkError):
    """Raised when a search job fails."""

    def __init__(
        self,
        message: str = "Search job failed.",
        sid: Optional[str] = None,
        dispatch_state: Optional[str] = None,
        **kwargs: Any,
    ):
        self.sid = sid
        self.dispatch_state = dispatch_state
        if sid:
            message = f"Search job '{sid}' failed."
        if dispatch_state:
            message = f"{message} State: {dispatch_state}"
        super().__init__(message, **kwargs)


def parse_error_response(response: requests.Response) -> Dict[str, Any]:
    """
    Parse error details from Splunk response.
    """
    try:
        data = response.json()
        messages = data.get("messages", [])
        if messages:
            return {
                "message": messages[0].get("text", "Unknown error"),
                "type": messages[0].get("type", "ERROR"),
                "code": messages[0].get("code"),
                "details": data,
            }
        return {"message": str(data), "details": data}
    except (json.JSONDecodeError, ValueError):
        return {"message": response.text or "Unknown error"}


def sanitize_error_message(message: str) -> str:
    """
    Sanitize error messages by calling the base sanitizer and adding Splunk-specific redactions.
    """
    sanitized = base_sanitize_error_message(message)
    # Splunk-specific patterns (if any) could be added here
    return sanitized


def handle_splunk_error(
    response: requests.Response, operation: str = "API request"
) -> None:
    """
    Handle Splunk API error response.
    """
    status_code = response.status_code
    error_info = parse_error_response(response)
    message = sanitize_error_message(error_info.get("message", "Unknown error"))
    details = error_info.get("details", {})

    error_kwargs: Dict[str, Any] = {
        "operation": operation,
        "details": details,
        "status_code": status_code,
        "response_data": response.text,
    }

    if status_code == 400:
        raise ValidationError(message, **error_kwargs)
    elif status_code == 401:
        raise AuthenticationError(message, **error_kwargs)
    elif status_code == 403:
        raise AuthorizationError(message, **error_kwargs)
    elif status_code == 404:
        raise NotFoundError(message, **error_kwargs)
    elif status_code == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            message,
            retry_after=int(retry_after) if retry_after else None,
            **error_kwargs,
        )
    elif status_code == 503:
        if "search" in message.lower() or "quota" in message.lower():
            raise SearchQuotaError(message, **error_kwargs)
        raise ServerError(message, **error_kwargs)
    elif status_code >= 500:
        raise ServerError(message, **error_kwargs)
    else:
        raise SplunkError(message, **error_kwargs)


def print_error(message: str, include_traceback: bool = False) -> None:
    """
    Print error message to stderr with formatting.
    """
    # This function is now a simple wrapper around the base printer
    base_print_error(message, show_traceback=include_traceback)


def handle_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator for handling errors in CLI scripts.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except SplunkError as e:
            # Use base_print_error with colorization
            base_print_error(f"Splunk Error: {e}", e)
            sys.exit(1)

    # Wrap with the base handler to catch generic and requests exceptions
    return base_handle_errors(wrapper)


def format_error_for_json(error: SplunkError) -> Dict[str, Any]:
    """
    Format error for JSON output.
    """
    return {
        "error": True,
        "type": type(error).__name__,
        "message": error.message,
        "status_code": error.status_code,
        "operation": error.operation,
        "details": error.details,
    }
