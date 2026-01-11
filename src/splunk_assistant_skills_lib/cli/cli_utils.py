"""CLI utility functions for Splunk Assistant Skills."""

from __future__ import annotations

import functools
import json
import sys
from typing import Any, Callable, TypeVar

import click

from splunk_assistant_skills_lib import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    SearchQuotaError,
    ServerError,
    SplunkError,
    ValidationError,
    print_error,
)

F = TypeVar("F", bound=Callable[..., Any])


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


def parse_json_arg(value: str | None) -> dict[str, Any] | None:
    """Parse a JSON string argument.

    Args:
        value: JSON string or None

    Returns:
        Parsed dict, or None if input was None/empty

    Raises:
        click.BadParameter: If JSON parsing fails
    """
    if not value:
        return None
    try:
        return json.loads(value)
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
    from splunk_assistant_skills_lib import (
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
    from splunk_assistant_skills_lib import (
        DEFAULT_EARLIEST_TIME,
        DEFAULT_LATEST_TIME,
        get_search_defaults,
        validate_time_modifier,
    )

    defaults = get_search_defaults()
    earliest_val = earliest or defaults.get("earliest_time", DEFAULT_EARLIEST_TIME)
    latest_val = latest or defaults.get("latest_time", DEFAULT_LATEST_TIME)
    return validate_time_modifier(earliest_val), validate_time_modifier(latest_val)


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

    Examples:
        >>> build_endpoint("/saved/searches")
        '/saved/searches'
        >>> build_endpoint("/saved/searches", app="search")
        '/servicesNS/-/search/saved/searches'
        >>> build_endpoint("/saved/searches", app="search", owner="admin")
        '/servicesNS/admin/search/saved/searches'
    """
    if app and owner:
        return f"/servicesNS/{owner}/{app}{base_path}"
    elif app:
        return f"/servicesNS/-/{app}{base_path}"
    return base_path
