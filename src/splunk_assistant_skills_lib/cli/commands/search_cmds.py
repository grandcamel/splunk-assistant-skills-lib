"""Search commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import click

from splunk_assistant_skills_lib import (
    build_search,
    estimate_search_complexity,
    export_csv,
    format_json,
    format_search_results,
    get_api_settings,
    optimize_spl,
    parse_spl_commands,
    print_success,
    print_warning,
    validate_spl,
    validate_spl_syntax,
    wait_for_job,
)

from ..cli_utils import (
    extract_sid_from_response,
    get_client_from_context,
    get_time_bounds,
    handle_cli_errors,
    parse_comma_list,
    validate_sid_callback,
)


@click.group()
def search() -> None:
    """SPL query execution commands.

    Execute Splunk searches in various modes: oneshot, normal, or blocking.
    """
    pass


@search.command()
@click.argument("spl")
@click.option("--earliest", "-e", help="Earliest time (e.g., -1h, -24h@h).")
@click.option("--latest", "-l", help="Latest time (e.g., now, -1h).")
@click.option("--count", "-c", type=int, help="Maximum number of results.")
@click.option("--fields", "-f", help="Comma-separated list of fields to return.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format.",
)
@click.option("--output-file", help="Write results to file (for csv).")
@click.pass_context
@handle_cli_errors
def oneshot(
    ctx: click.Context,
    spl: str,
    earliest: str | None,
    latest: str | None,
    count: int | None,
    fields: str | None,
    output: str,
    output_file: str | None,
) -> None:
    """Execute a oneshot search (results returned inline).

    Best for ad-hoc queries with results under 50,000 rows.

    Example:
        splunk-as search oneshot "index=main | stats count by sourcetype"
    """
    earliest, latest = get_time_bounds(earliest, latest)
    fields_list = parse_comma_list(fields)
    api_settings = get_api_settings()

    spl = validate_spl(spl)
    search_spl = build_search(
        spl, earliest_time=earliest, latest_time=latest, fields=fields_list
    )
    client = get_client_from_context(ctx)

    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": search_spl,
            "earliest_time": earliest,
            "latest_time": latest,
            "count": count or 50000,
            "output_mode": "json",
        },
        timeout=api_settings.get("search_timeout", 300),
        operation="oneshot search",
    )

    results = response.get("results", [])
    _output_search_results(results, output, output_file, fields_list)


@search.command()
@click.argument("spl")
@click.option("--earliest", "-e", help="Earliest time.")
@click.option("--latest", "-l", help="Latest time.")
@click.option("--wait/--no-wait", default=False, help="Wait for job completion.")
@click.option("--timeout", type=int, default=300, help="Timeout in seconds.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def normal(
    ctx: click.Context,
    spl: str,
    earliest: str | None,
    latest: str | None,
    wait: bool,
    timeout: int,
    output: str,
) -> None:
    """Execute a normal (async) search.

    Returns a search ID (SID) immediately. Use 'job status' to check progress.

    Example:
        splunk-as search normal "index=main | stats count" --wait
    """
    earliest, latest = get_time_bounds(earliest, latest)
    spl = validate_spl(spl)
    search_spl = build_search(spl, earliest_time=earliest, latest_time=latest)
    client = get_client_from_context(ctx)

    response = client.post(
        "/search/v2/jobs",
        data={
            "search": search_spl,
            "exec_mode": "normal",
            "earliest_time": earliest,
            "latest_time": latest,
        },
        operation="create search job",
    )

    sid = extract_sid_from_response(response)

    if wait:
        wait_for_job(client, sid, timeout=timeout, show_progress=True)
        results = client.get(
            f"/search/v2/jobs/{quote(sid, safe='')}/results",
            params={"output_mode": "json", "count": 0},
            operation="get results",
        ).get("results", [])

        if output == "json":
            click.echo(format_json({"sid": sid, "results": results}))
        else:
            click.echo(format_search_results(results))
            print_success(f"Completed: {len(results)} results")
    else:
        if output == "json":
            click.echo(format_json({"sid": sid, "status": "created"}))
        else:
            print_success(f"Job created: {sid}")
            click.echo(f"Use: splunk-as job status {sid}")


@search.command()
@click.argument("spl")
@click.option("--earliest", "-e", help="Earliest time.")
@click.option("--latest", "-l", help="Latest time.")
@click.option("--timeout", type=int, default=300, help="Timeout in seconds.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def blocking(
    ctx: click.Context,
    spl: str,
    earliest: str | None,
    latest: str | None,
    timeout: int,
    output: str,
) -> None:
    """Execute a blocking search (waits for completion).

    Example:
        splunk-as search blocking "index=main | head 10" --timeout 60
    """
    earliest, latest = get_time_bounds(earliest, latest)
    spl = validate_spl(spl)
    search_spl = build_search(spl, earliest_time=earliest, latest_time=latest)
    client = get_client_from_context(ctx)

    response = client.post(
        "/search/v2/jobs",
        data={
            "search": search_spl,
            "exec_mode": "blocking",
            "earliest_time": earliest,
            "latest_time": latest,
        },
        timeout=timeout,
        operation="blocking search",
    )

    sid = extract_sid_from_response(response)
    results = client.get(
        f"/search/v2/jobs/{quote(sid, safe='')}/results",
        params={"output_mode": "json", "count": 0},
        operation="get results",
    ).get("results", [])

    if output == "json":
        click.echo(format_json({"sid": sid, "results": results}))
    else:
        click.echo(format_search_results(results))
        print_success(f"Completed: {len(results)} results")


@search.command()
@click.argument("spl")
@click.option(
    "--suggestions", "-s", is_flag=True, help="Show optimization suggestions."
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def validate(ctx: click.Context, spl: str, suggestions: bool, output: str) -> None:
    """Validate SPL syntax without executing.

    Example:
        splunk-as search validate "index=main | stats count"
    """
    is_valid, issues = validate_spl_syntax(spl)
    commands = parse_spl_commands(spl)
    complexity = estimate_search_complexity(spl)
    _, optimization_suggestions = optimize_spl(spl)

    result: dict[str, Any] = {
        "valid": is_valid,
        "issues": issues,
        "commands": [{"name": c[0], "args": c[1]} for c in commands],
        "complexity": complexity,
        "suggestions": optimization_suggestions if suggestions else [],
    }

    if output == "json":
        click.echo(format_json(result))
    else:
        if result["valid"]:
            print_success("SPL syntax is valid")
        else:
            print_warning("SPL syntax issues found:")
            for issue in result["issues"]:
                click.echo(f"  - {issue}")

        click.echo(f"\nComplexity: {result['complexity']}")
        click.echo(f"Commands: {' | '.join(c['name'] for c in result['commands'])}")

        if suggestions and result["suggestions"]:
            click.echo("\nOptimization suggestions:")
            for s in result["suggestions"]:
                click.echo(f"  - {s}")


@search.command()
@click.argument("sid", callback=validate_sid_callback)
@click.option(
    "--count", "-c", type=int, default=0, help="Maximum results to return (0=all)."
)
@click.option("--offset", type=int, default=0, help="Offset for pagination.")
@click.option("--fields", "-f", help="Comma-separated fields to return.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format.",
)
@click.option("--output-file", help="Write results to file.")
@click.pass_context
@handle_cli_errors
def results(
    ctx: click.Context,
    sid: str,
    count: int,
    offset: int,
    fields: str | None,
    output: str,
    output_file: str | None,
) -> None:
    """Get results from a completed search job.

    Example:
        splunk-as search results 1703779200.12345 --count 100
    """
    fields_list = parse_comma_list(fields)
    client = get_client_from_context(ctx)

    params = {"output_mode": "json", "count": count, "offset": offset}
    if fields_list:
        params["field_list"] = ",".join(fields_list)

    result_data = client.get(
        f"/search/v2/jobs/{quote(sid, safe='')}/results", params=params, operation="get results"
    ).get("results", [])

    _output_search_results(result_data, output, output_file, fields_list)


@search.command()
@click.argument("sid", callback=validate_sid_callback)
@click.option("--count", "-c", type=int, default=100, help="Maximum results to return.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def preview(ctx: click.Context, sid: str, count: int, output: str) -> None:
    """Get preview results from a running search job.

    Example:
        splunk-as search preview 1703779200.12345
    """
    client = get_client_from_context(ctx)

    results = client.get(
        f"/search/v2/jobs/{quote(sid, safe='')}/results_preview",
        params={"output_mode": "json", "count": count},
        operation="get preview",
    ).get("results", [])

    if output == "json":
        click.echo(format_json(results))
    else:
        click.echo(format_search_results(results))
        click.echo(f"Preview: {len(results)} results (job may still be running)")


def _output_search_results(
    results: list, output: str, output_file: str | None, fields_list: list | None
) -> None:
    """Helper to output search results in various formats."""
    if output == "json":
        click.echo(format_json(results))
    elif output == "csv":
        if output_file:
            export_csv(results, output_file, columns=fields_list)
            print_success(f"Results written to {output_file}")
        else:
            click.echo(
                format_search_results(results, fields=fields_list, output_format="csv")
            )
    else:
        click.echo(format_search_results(results, fields=fields_list))
        print_success(f"Found {len(results)} results")
