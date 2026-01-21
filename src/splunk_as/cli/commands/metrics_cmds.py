"""Metrics commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import re

import click

from splunk_as import (
    ValidationError,
    format_json,
    format_search_results,
    print_success,
    quote_field_value,
    validate_index_name,
)

from ..cli_utils import (
    get_client_from_context,
    get_time_bounds,
    handle_cli_errors,
    output_results,
)

# Valid aggregation functions for mstats
VALID_AGG_FUNCTIONS = frozenset({"avg", "sum", "min", "max", "count"})

# Valid span format pattern (e.g., 1m, 5m, 1h, 30s)
SPAN_PATTERN = re.compile(r"^\d+[smhd]$")


def _validate_field_name(field: str, param_name: str = "field") -> str:
    """Validate field name to prevent SPL injection.

    Args:
        field: Field name to validate
        param_name: Parameter name for error messages

    Returns:
        Validated field name

    Raises:
        ValidationError: If field name is invalid
    """
    if not field or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.:]*$", field):
        raise ValidationError(
            f"Invalid field name: {field}",
            operation="validation",
            details={"field": param_name},
        )
    return field


def _validate_metric_name(metric: str, param_name: str = "metric_name") -> str:
    """Validate metric name to prevent SPL injection.

    Metric names can contain alphanumeric, underscore, dot, and hyphen.

    Args:
        metric: Metric name to validate
        param_name: Parameter name for error messages

    Returns:
        Validated metric name

    Raises:
        ValidationError: If metric name is invalid
    """
    if not metric or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_.\-]*$", metric):
        raise ValidationError(
            f"Invalid metric name: {metric}",
            operation="validation",
            details={"field": param_name},
        )
    return metric


def _validate_span(span: str) -> str:
    """Validate span format.

    Args:
        span: Span value (e.g., 1m, 5m, 1h)

    Returns:
        Validated span

    Raises:
        ValidationError: If span format is invalid
    """
    if not SPAN_PATTERN.match(span):
        raise ValidationError(
            f"Invalid span format: {span}. Use format like 1m, 5m, 1h, 30s",
            operation="validation",
            details={"field": "span"},
        )
    return span


@click.group()
def metrics() -> None:
    """Real-time metrics operations.

    Query and analyze Splunk metrics using mstats and mcatalog.
    """
    pass


@metrics.command(name="list")
@click.option("--index", "-i", help="Filter by metrics index.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_metrics(ctx: click.Context, index: str | None, output: str) -> None:
    """List available metrics.

    Example:
        splunk-as metrics list --index my_metrics
    """
    client = get_client_from_context(ctx)
    spl = "| mcatalog values(metric_name) as metrics"
    if index:
        # Validate and quote index to prevent SPL injection
        validate_index_name(index)
        spl += f' WHERE index="{index}"'
    spl += " | mvexpand metrics | sort metrics"

    response = client.post(
        "/search/jobs/oneshot",
        data={"search": spl, "output_mode": "json", "count": 1000},
        operation="list metrics",
    )
    results = response.get("results", [])

    if output == "json":
        click.echo(format_json(results))
    else:
        if not results:
            click.echo("No metrics found.")
            return
        metrics_list = [r.get("metrics", "") for r in results if r.get("metrics")]
        for metric in metrics_list[:50]:
            click.echo(f"  - {metric}")
        print_success(f"Found {len(metrics_list)} metrics")


@metrics.command()
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def indexes(ctx: click.Context, output: str) -> None:
    """List metrics indexes.

    Example:
        splunk-as metrics indexes
    """
    client = get_client_from_context(ctx)
    response = client.get(
        "/data/indexes", params={"datatype": "metric"}, operation="list metrics indexes"
    )

    indexes_list = [
        {
            "name": entry.get("name"),
            "totalEventCount": entry.get("content", {}).get("totalEventCount", 0),
            "currentDBSizeMB": entry.get("content", {}).get("currentDBSizeMB", 0),
        }
        for entry in response.get("entry", [])
        if entry.get("content", {}).get("datatype") == "metric"
    ]
    output_results(
        indexes_list, output, success_msg=f"Found {len(indexes_list)} metrics indexes"
    )


@metrics.command()
@click.argument("metric_name")
@click.option("--index", "-i", help="Metrics index.")
@click.option("--earliest", "-e", default="-1h", help="Earliest time.")
@click.option("--latest", "-l", default="now", help="Latest time.")
@click.option("--span", default="1m", help="Time span for aggregation.")
@click.option(
    "--agg",
    type=click.Choice(["avg", "sum", "min", "max", "count"]),
    default="avg",
    help="Aggregation function.",
)
@click.option("--split-by", help="Field to split by.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def mstats(
    ctx: click.Context,
    metric_name: str,
    index: str | None,
    earliest: str,
    latest: str,
    span: str,
    agg: str,
    split_by: str | None,
    output: str,
) -> None:
    """Query metrics using mstats.

    Example:
        splunk-as metrics mstats cpu.percent --index my_metrics --span 5m
    """
    # Validate all user inputs to prevent SPL injection
    if agg not in VALID_AGG_FUNCTIONS:
        raise ValidationError(
            f"Invalid aggregation function: {agg}",
            operation="validation",
            details={"field": "agg"},
        )
    _validate_metric_name(metric_name)
    _validate_span(span)

    client = get_client_from_context(ctx)
    earliest, latest = get_time_bounds(earliest, latest)

    # Quote metric_name for defense-in-depth
    spl = f'| mstats {agg}("{metric_name}") as value'
    if index:
        validate_index_name(index)
        spl += f' WHERE index="{index}"'
    if split_by:
        _validate_field_name(split_by, "split_by")
        spl += f" BY {split_by}"
    spl += f" span={span}"

    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": spl,
            "earliest_time": earliest,
            "latest_time": latest,
            "output_mode": "json",
            "count": 1000,
        },
        operation="mstats query",
    )
    results = response.get("results", [])

    if output == "json":
        click.echo(format_json(results))
    else:
        if not results:
            click.echo(f"No data found for metric: {metric_name}")
            return
        click.echo(format_search_results(results))
        print_success(f"Found {len(results)} data points")


@metrics.command()
@click.option("--index", "-i", help="Metrics index.")
@click.option("--metric", "-m", help="Filter by metric name pattern.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def mcatalog(
    ctx: click.Context, index: str | None, metric: str | None, output: str
) -> None:
    """Explore metrics catalog.

    Example:
        splunk-as metrics mcatalog --index my_metrics --metric "cpu.*"
    """
    client = get_client_from_context(ctx)
    spl = "| mcatalog values(metric_name) as metric_name, values(_dims) as dimensions"

    where_clause = []
    if index:
        # Validate and quote index to prevent SPL injection
        validate_index_name(index)
        where_clause.append(f'index="{index}"')
    if metric:
        # Validate metric pattern (allow wildcards for catalog search)
        # Escape any quotes and validate basic format
        if not re.match(r"^[a-zA-Z_*][a-zA-Z0-9_.\-*]*$", metric):
            raise ValidationError(
                f"Invalid metric pattern: {metric}",
                operation="validation",
                details={"field": "metric"},
            )
        safe_metric = metric.replace('"', '\\"')
        where_clause.append(f'metric_name="{safe_metric}"')
    if where_clause:
        spl += f" WHERE {' AND '.join(where_clause)}"
    spl += " | stats count by metric_name, dimensions"

    response = client.post(
        "/search/jobs/oneshot",
        data={"search": spl, "output_mode": "json", "count": 1000},
        operation="mcatalog query",
    )
    results = response.get("results", [])
    output_results(
        results[:50], output, success_msg=f"Found {len(results)} catalog entries"
    )
