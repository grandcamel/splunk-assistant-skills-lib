"""Job management commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_as import (
    build_search,
    cancel_job,
    delete_job,
    finalize_job,
    format_job_status,
    format_json,
    format_table,
    get_dispatch_state,
    list_jobs,
    pause_job,
    print_success,
    set_job_ttl,
    unpause_job,
    validate_spl,
    wait_for_job,
)

from ..cli_utils import (
    extract_sid_from_response,
    get_client_from_context,
    get_time_bounds,
    handle_cli_errors,
    validate_sid_callback,
)


@click.group()
def job() -> None:
    """Search job lifecycle management.

    Create, monitor, control, and clean up Splunk search jobs.
    """
    pass


@job.command()
@click.argument("spl")
@click.option("--earliest", "-e", help="Earliest time.")
@click.option("--latest", "-l", help="Latest time.")
@click.option(
    "--exec-mode",
    type=click.Choice(["normal", "blocking"]),
    default="normal",
    help="Execution mode.",
)
@click.option("--app", help="App context for search.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def create(
    ctx: click.Context,
    spl: str,
    earliest: str | None,
    latest: str | None,
    exec_mode: str,
    app: str | None,
    output: str,
) -> None:
    """Create a new search job.

    Example:
        splunk-as job create "index=main | stats count"
    """
    earliest, latest = get_time_bounds(earliest, latest)
    spl = validate_spl(spl)
    search_spl = build_search(spl, earliest_time=earliest, latest_time=latest)
    client = get_client_from_context(ctx)

    data = {
        "search": search_spl,
        "exec_mode": exec_mode,
        "earliest_time": earliest,
        "latest_time": latest,
    }
    if app:
        data["namespace"] = app

    response = client.post(
        "/search/v2/jobs",
        data=data,
        timeout=(
            client.DEFAULT_SEARCH_TIMEOUT if exec_mode == "blocking" else client.timeout
        ),
        operation="create search job",
    )

    sid = extract_sid_from_response(response)

    if output == "json":
        click.echo(
            format_json(
                {
                    "sid": sid,
                    "exec_mode": exec_mode,
                    "search": search_spl,
                    "earliest_time": earliest,
                    "latest_time": latest,
                }
            )
        )
    else:
        print_success(f"Job created: {sid}")
        search_display = search_spl[:80] + ("..." if len(search_spl) > 80 else "")
        click.echo(f"Search: {search_display}")
        click.echo(f"Mode: {exec_mode}")
        click.echo(f"Time range: {earliest} to {latest}")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def status(ctx: click.Context, sid: str, output: str) -> None:
    """Get the status of a search job.

    Example:
        splunk-as job status 1703779200.12345
    """
    client = get_client_from_context(ctx)
    progress = get_dispatch_state(client, sid)

    if output == "json":
        click.echo(
            format_json(
                {
                    "sid": progress.sid,
                    "state": progress.state.value,
                    "progress": progress.progress_percent,
                    "event_count": progress.event_count,
                    "result_count": progress.result_count,
                    "scan_count": progress.scan_count,
                    "run_duration": progress.run_duration,
                    "is_done": progress.is_done,
                    "is_failed": progress.is_failed,
                    "is_paused": progress.is_paused,
                }
            )
        )
    else:
        click.echo(format_job_status({"content": progress.data}))


@job.command(name="list")
@click.option("--count", "-c", type=int, default=50, help="Maximum jobs to list.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_jobs_cmd(ctx: click.Context, count: int, output: str) -> None:
    """List search jobs.

    Example:
        splunk-as job list --count 10
    """
    client = get_client_from_context(ctx)
    jobs = list_jobs(client, count=count)

    if output == "json":
        click.echo(format_json(jobs))
    else:
        if not jobs:
            click.echo("No active jobs found.")
            return

        # Format for display
        display_data = []
        for job_info in jobs:
            display_data.append(
                {
                    "SID": job_info.get("sid", "")[:30],
                    "State": job_info.get("dispatchState", "Unknown"),
                    "Progress": f"{float(job_info.get('doneProgress', 0)) * 100:.0f}%",
                    "Results": job_info.get("resultCount", 0),
                    "Duration": f"{float(job_info.get('runDuration', 0)):.1f}s",
                }
            )

        click.echo(
            format_table(
                display_data,
                columns=["SID", "State", "Progress", "Results", "Duration"],
            )
        )
        click.echo(f"\nTotal: {len(jobs)} jobs")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.option("--timeout", type=int, default=300, help="Timeout in seconds.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress updates.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def poll(ctx: click.Context, sid: str, timeout: int, quiet: bool, output: str) -> None:
    """Poll a job until completion.

    Example:
        splunk-as job poll 1703779200.12345 --timeout 60
    """
    client = get_client_from_context(ctx)

    progress = wait_for_job(
        client,
        sid,
        timeout=timeout,
        show_progress=not quiet,
    )

    if output == "json":
        click.echo(
            format_json(
                {
                    "sid": progress.sid,
                    "state": progress.state.value,
                    "result_count": progress.result_count,
                    "event_count": progress.event_count,
                    "run_duration": progress.run_duration,
                }
            )
        )
    else:
        print_success(f"Job completed: {progress.state.value}")
        click.echo(f"Results: {progress.result_count:,}")
        click.echo(f"Events: {progress.event_count:,}")
        click.echo(f"Duration: {progress.run_duration:.2f}s")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.pass_context
@handle_cli_errors
def cancel(ctx: click.Context, sid: str) -> None:
    """Cancel a running search job.

    Example:
        splunk-as job cancel 1703779200.12345
    """
    client = get_client_from_context(ctx)
    cancel_job(client, sid)
    print_success(f"Job cancelled: {sid}")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.pass_context
@handle_cli_errors
def pause(ctx: click.Context, sid: str) -> None:
    """Pause a running search job.

    Example:
        splunk-as job pause 1703779200.12345
    """
    client = get_client_from_context(ctx)
    pause_job(client, sid)
    print_success(f"Job paused: {sid}")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.pass_context
@handle_cli_errors
def unpause(ctx: click.Context, sid: str) -> None:
    """Resume a paused search job.

    Example:
        splunk-as job unpause 1703779200.12345
    """
    client = get_client_from_context(ctx)
    unpause_job(client, sid)
    print_success(f"Job resumed: {sid}")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.pass_context
@handle_cli_errors
def finalize(ctx: click.Context, sid: str) -> None:
    """Finalize a search job (stop and return current results).

    Example:
        splunk-as job finalize 1703779200.12345
    """
    client = get_client_from_context(ctx)
    finalize_job(client, sid)
    print_success(f"Job finalized: {sid}")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.pass_context
@handle_cli_errors
def delete(ctx: click.Context, sid: str) -> None:
    """Delete a search job.

    Example:
        splunk-as job delete 1703779200.12345
    """
    client = get_client_from_context(ctx)
    delete_job(client, sid)
    print_success(f"Job deleted: {sid}")


@job.command()
@click.argument("sid", callback=validate_sid_callback)
@click.argument("ttl_value", type=int)
@click.pass_context
@handle_cli_errors
def ttl(ctx: click.Context, sid: str, ttl_value: int) -> None:
    """Set the TTL (time-to-live) for a search job.

    Example:
        splunk-as job ttl 1703779200.12345 3600
    """
    client = get_client_from_context(ctx)
    set_job_ttl(client, sid, ttl=ttl_value)
    print_success(f"Job TTL set to {ttl_value}s: {sid}")
