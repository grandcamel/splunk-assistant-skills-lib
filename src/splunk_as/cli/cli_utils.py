"""CLI utility functions for Splunk Assistant Skills."""

from __future__ import annotations

import functools
import json
import sys
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

import click

from splunk_as import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    SearchQuotaError,
    ServerError,
    SplunkError,
    ValidationError,
    get_splunk_client,
    print_error,
    validate_path_component,
    validate_sid,
)

if TYPE_CHECKING:
    from splunk_as import SplunkClient

F = TypeVar("F", bound=Callable[..., Any])


def get_client_from_context(ctx: click.Context) -> "SplunkClient":
    """Get or create a shared SplunkClient from the Click context.

    This provides a single client instance shared across all commands in a CLI
    invocation, improving performance and testability.

    Args:
        ctx: Click context object

    Returns:
        Shared SplunkClient instance
    """
    ctx.ensure_object(dict)
    if ctx.obj.get("_client") is None:
        ctx.obj["_client"] = get_splunk_client()
    return cast("SplunkClient", ctx.obj["_client"])


def validate_sid_callback(
    ctx: click.Context, param: click.Parameter, value: str
) -> str:
    """Click callback to validate SID parameter.

    Use this as a callback on Click arguments/options that accept a SID.

    Args:
        ctx: Click context
        param: Click parameter
        value: SID value to validate

    Returns:
        Validated SID

    Raises:
        click.BadParameter: If SID is invalid
    """
    try:
        return validate_sid(value)
    except ValidationError as e:
        raise click.BadParameter(str(e))


def extract_sid_from_response(response: dict[str, Any]) -> str:
    """Extract SID from job creation response with consistent fallback logic.

    Handles both v1 and v2 API response formats from Splunk.

    Args:
        response: Job creation response dict

    Returns:
        Extracted SID string

    Raises:
        ValueError: If SID could not be extracted from response
    """
    # Direct sid field (v2 API)
    if sid := response.get("sid"):
        return str(sid)

    # Entry format (v1 API)
    if entries := response.get("entry"):
        if entries and len(entries) > 0:
            entry = entries[0]
            # Try name field first
            if name := entry.get("name"):
                return str(name)
            # Fall back to content.sid
            if content := entry.get("content"):
                if sid := content.get("sid"):
                    return str(sid)

    raise ValueError("Could not extract SID from response")


def handle_cli_errors(func: F) -> F:
    """Decorator to handle exceptions in CLI commands.

    Catches SplunkError exceptions and prints user-friendly error messages,
    then exits with appropriate exit codes.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            print_error(f"Validation error: {e}")
            sys.exit(1)
        except AuthenticationError as e:
            print_error(f"Authentication failed: {e}")
            sys.exit(2)
        except AuthorizationError as e:
            print_error(f"Authorization denied: {e}")
            sys.exit(3)
        except NotFoundError as e:
            print_error(f"Not found: {e}")
            sys.exit(4)
        except RateLimitError as e:
            print_error(f"Rate limit exceeded: {e}")
            sys.exit(5)
        except SearchQuotaError as e:
            print_error(f"Search quota exceeded: {e}")
            sys.exit(6)
        except ServerError as e:
            print_error(f"Server error: {e}")
            sys.exit(7)
        except SplunkError as e:
            print_error(f"Splunk error: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print_error("Interrupted by user")
            sys.exit(130)
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            sys.exit(1)

    return wrapper  # type: ignore[return-value]


def parse_comma_list(value: str | None) -> list[str] | None:
    """Parse a comma-separated string into a list.

    Args:
        value: Comma-separated string or None

    Returns:
        List of stripped strings, or None if input was None/empty
    """
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


# Maximum JSON input size (1 MB) to prevent DoS via large payloads
MAX_JSON_SIZE = 1024 * 1024


def parse_json_arg(
    value: str | None, max_size: int = MAX_JSON_SIZE
) -> dict[str, Any] | None:
    """Parse a JSON string argument with size limit.

    Args:
        value: JSON string or None
        max_size: Maximum allowed JSON size in bytes (default 1 MB)

    Returns:
        Parsed dict, or None if input was None/empty

    Raises:
        click.BadParameter: If JSON parsing fails or size exceeds limit
    """
    if not value:
        return None
    if len(value) > max_size:
        raise click.BadParameter(
            f"JSON too large ({len(value):,} bytes, max {max_size:,} bytes)"
        )
    try:
        return cast(dict[str, Any], json.loads(value))
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON: {e}")


def validate_positive_int(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    """Click callback to validate positive integers."""
    if value is not None and value <= 0:
        raise click.BadParameter("must be a positive integer")
    return value


def validate_non_negative_int(
    ctx: click.Context, param: click.Parameter, value: int | None
) -> int | None:
    """Click callback to validate non-negative integers."""
    if value is not None and value < 0:
        raise click.BadParameter("must be a non-negative integer")
    return value


def output_results(
    data: Any,
    output_format: str = "text",
    columns: list[str] | None = None,
    success_msg: str | None = None,
) -> None:
    """Output results in the specified format.

    Args:
        data: Results to output (list of dicts, dict, or string)
        output_format: One of "json", "text", "csv"
        columns: Column names for table/csv output
        success_msg: Optional success message for text output
    """
    from splunk_as import (
        export_csv_string,
        format_json,
        format_table,
        print_success,
    )

    if output_format == "json":
        click.echo(format_json(data))
    elif output_format == "csv":
        if isinstance(data, list):
            click.echo(export_csv_string(data, columns))
        else:
            click.echo(format_json(data))
    else:
        if isinstance(data, list) and data:
            click.echo(format_table(data, columns=columns))
        elif isinstance(data, dict):
            click.echo(format_json(data))
        elif data:
            click.echo(data)
        if success_msg:
            print_success(success_msg)


def get_time_bounds(earliest: str | None, latest: str | None) -> tuple[str, str]:
    """Get time bounds with defaults applied.

    Args:
        earliest: Earliest time or None for default
        latest: Latest time or None for default

    Returns:
        Tuple of (earliest, latest) with defaults applied
    """
    from splunk_as import (
        DEFAULT_EARLIEST_TIME,
        DEFAULT_LATEST_TIME,
        get_search_defaults,
        validate_time_modifier,
    )

    defaults = get_search_defaults()
    earliest_val = earliest or defaults.get("earliest_time", DEFAULT_EARLIEST_TIME)
    latest_val = latest or defaults.get("latest_time", DEFAULT_LATEST_TIME)
    return validate_time_modifier(earliest_val), validate_time_modifier(latest_val)


def with_time_bounds(func: F) -> F:
    """Decorator to add standard time bound options to a Click command.

    Adds --earliest/-e and --latest/-l options to the decorated command.
    These options accept Splunk time modifiers like -1h, -24h@h, now, etc.

    Example:
        @search.command()
        @click.argument("spl")
        @with_time_bounds
        @click.pass_context
        def oneshot(ctx, spl, earliest, latest):
            earliest, latest = get_time_bounds(earliest, latest)
            ...
    """
    func = click.option(
        "--latest",
        "-l",
        default=None,
        help="Latest time (e.g., now, -1h). Default from config.",
    )(func)
    func = click.option(
        "--earliest",
        "-e",
        default=None,
        help="Earliest time (e.g., -1h, -24h@h). Default from config.",
    )(func)
    return func


def build_endpoint(
    base_path: str,
    app: str | None = None,
    owner: str | None = None,
) -> str:
    """Build a Splunk REST API endpoint with optional namespace.

    Args:
        base_path: Base endpoint path (e.g., "/saved/searches")
        app: App context (uses "-" wildcard if owner not specified)
        owner: Owner context

    Returns:
        Full endpoint path with namespace prefix if app/owner specified

    Raises:
        ValidationError: If app or owner contain path traversal attempts

    Examples:
        >>> build_endpoint("/saved/searches")
        '/saved/searches'
        >>> build_endpoint("/saved/searches", app="search")
        '/servicesNS/-/search/saved/searches'
        >>> build_endpoint("/saved/searches", app="search", owner="admin")
        '/servicesNS/admin/search/saved/searches'
    """
    # Validate path components to prevent URL path injection
    if app:
        app = validate_path_component(app, "app")
    if owner:
        owner = validate_path_component(owner, "owner")

    if app and owner:
        return f"/servicesNS/{owner}/{app}{base_path}"
    elif app:
        return f"/servicesNS/-/{app}{base_path}"
    return base_path
