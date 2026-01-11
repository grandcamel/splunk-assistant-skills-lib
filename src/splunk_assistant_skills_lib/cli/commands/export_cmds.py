"""Export commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import (
    build_search,
    get_api_settings,
    get_splunk_client,
    print_info,
    print_success,
    validate_sid,
    validate_spl,
    wait_for_job,
)

from ..cli_utils import get_time_bounds, handle_cli_errors


@click.group()
def export():
    """Data export and extraction commands.

    Export search results in various formats for ETL and analysis.
    """
    pass


@export.command()
@click.argument("spl")
@click.option("--output-file", "-o", required=True, help="Output file path.")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["csv", "json", "xml"]),
    default="csv",
    help="Export format.",
)
@click.option("--earliest", "-e", help="Earliest time.")
@click.option("--latest", "-l", help="Latest time.")
@click.option("--fields", help="Comma-separated fields to export.")
@click.option("--progress", is_flag=True, help="Show progress.")
@click.pass_context
@handle_cli_errors
def results(ctx, spl, output_file, output_format, earliest, latest, fields, progress):
    """Export results from a search to file.

    Example:
        splunk-as export results "index=main | stats count by host" -o results.csv
    """
    api_settings = get_api_settings()
    spl = validate_spl(spl)
    earliest, latest = get_time_bounds(earliest, latest)

    search_spl = build_search(spl, earliest_time=earliest, latest_time=latest)

    client = get_splunk_client()

    # Create job
    print_info("Creating search job...")
    response = client.post(
        "/search/v2/jobs",
        data={
            "search": search_spl,
            "exec_mode": "normal",
            "earliest_time": earliest,
            "latest_time": latest,
        },
        operation="create export job",
    )

    sid = response.get("sid")
    if not sid and "entry" in response:
        sid = response["entry"][0].get("name")

    # Wait for completion
    print_info(f"Waiting for job {sid}...")
    job_progress = wait_for_job(
        client,
        sid,
        timeout=api_settings.get("search_timeout", 300),
        show_progress=progress,
    )

    print_info(f"Exporting {job_progress.result_count:,} results...")

    # Build export params
    params = {
        "output_mode": output_format,
        "count": 0,
    }
    if fields:
        params["field_list"] = fields

    # Stream to file
    bytes_written = 0
    with open(output_file, "wb") as f:
        for chunk in client.stream_results(
            f"/search/v2/jobs/{sid}/results",
            params=params,
            timeout=api_settings.get("search_timeout", 300),
            operation="export results",
        ):
            f.write(chunk)
            bytes_written += len(chunk)

    print_success(f"Exported {job_progress.result_count:,} results to {output_file}")
    print_info(f"File size: {bytes_written / 1024 / 1024:.2f} MB")


@export.command()
@click.argument("sid")
@click.option("--output-file", "-o", required=True, help="Output file path.")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["csv", "json", "xml"]),
    default="csv",
    help="Export format.",
)
@click.option("--count", "-c", type=int, help="Maximum results to export.")
@click.pass_context
@handle_cli_errors
def job(ctx, sid, output_file, output_format, count):
    """Export results from an existing search job.

    Example:
        splunk-as export job 1703779200.12345 -o results.csv
    """
    sid = validate_sid(sid)
    client = get_splunk_client()
    api_settings = get_api_settings()

    params = {
        "output_mode": output_format,
        "count": count or 0,
    }

    print_info(f"Exporting results from job {sid}...")

    bytes_written = 0
    with open(output_file, "wb") as f:
        for chunk in client.stream_results(
            f"/search/v2/jobs/{sid}/results",
            params=params,
            timeout=api_settings.get("search_timeout", 300),
            operation="export job results",
        ):
            f.write(chunk)
            bytes_written += len(chunk)

    print_success(f"Exported to {output_file}")
    print_info(f"File size: {bytes_written / 1024 / 1024:.2f} MB")


@export.command()
@click.argument("spl")
@click.option("--earliest", "-e", help="Earliest time.")
@click.option("--latest", "-l", help="Latest time.")
@click.pass_context
@handle_cli_errors
def estimate(ctx, spl, earliest, latest):
    """Estimate the size of an export before running it.

    Example:
        splunk-as export estimate "index=main | head 10000"
    """
    spl = validate_spl(spl)
    earliest, latest = get_time_bounds(earliest, latest)

    # Add stats count to estimate
    estimate_spl = f"{spl} | stats count"
    search_spl = build_search(estimate_spl, earliest_time=earliest, latest_time=latest)

    client = get_splunk_client()

    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": search_spl,
            "earliest_time": earliest,
            "latest_time": latest,
            "output_mode": "json",
        },
        operation="estimate export size",
    )

    results = response.get("results", [])
    count = int(results[0].get("count", 0)) if results else 0

    click.echo(f"Estimated results: {count:,}")
    click.echo(f"Time range: {earliest} to {latest}")

    # Rough estimate: ~200 bytes per result for CSV
    estimated_size_mb = (count * 200) / (1024 * 1024)
    click.echo(f"Estimated file size: ~{estimated_size_mb:.2f} MB (rough estimate)")
