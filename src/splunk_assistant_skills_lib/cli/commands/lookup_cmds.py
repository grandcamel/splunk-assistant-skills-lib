"""Lookup commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import os

import click

from splunk_assistant_skills_lib import (
    format_json,
    format_search_results,
    format_table,
    print_success,
    print_warning,
    validate_count,
    validate_file_path,
    validate_path_component,
)

from ..cli_utils import build_endpoint, get_client_from_context, handle_cli_errors


@click.group()
def lookup() -> None:
    """CSV and lookup file management.

    Upload, download, and manage lookup files in Splunk.
    """
    pass


@lookup.command(name="list")
@click.option("--app", "-a", help="Filter by app.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_lookups(ctx: click.Context, app: str | None, output: str) -> None:
    """List all lookup files.

    Example:
        splunk-as lookup list --app search
    """
    client = get_client_from_context(ctx)
    endpoint = build_endpoint("/data/lookup-table-files", app=app)
    response = client.get(endpoint, operation="list lookups")

    lookups = []
    for entry in response.get("entry", []):
        lookups.append(
            {
                "name": entry.get("name"),
                "app": entry.get("acl", {}).get("app", ""),
                "owner": entry.get("acl", {}).get("owner", ""),
            }
        )

    if output == "json":
        click.echo(format_json(lookups))
    else:
        if not lookups:
            click.echo("No lookup files found.")
            return
        click.echo(format_table(lookups))
        print_success(f"Found {len(lookups)} lookup files")


@lookup.command()
@click.argument("lookup_name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format.",
)
@click.option("--count", "-c", type=int, default=100, help="Maximum rows to show.")
@click.pass_context
@handle_cli_errors
def get(
    ctx: click.Context, lookup_name: str, app: str, output: str, count: int
) -> None:
    """Get contents of a lookup file.

    Example:
        splunk-as lookup get users.csv --app search
    """
    # Validate lookup_name to prevent SPL injection
    safe_lookup_name = validate_path_component(lookup_name, "lookup_name")
    # Validate count to prevent resource exhaustion
    validated_count = validate_count(count)

    client = get_client_from_context(ctx)

    # Use inputlookup to get contents (quote name for defense-in-depth)
    search = f'| inputlookup "{safe_lookup_name}" | head {validated_count}'
    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": search,
            "namespace": app,
            "output_mode": "json",
            "count": validated_count,
        },
        operation="get lookup contents",
    )

    results = response.get("results", [])

    if output == "json":
        click.echo(format_json(results))
    elif output == "csv":
        click.echo(format_search_results(results, output_format="csv"))
    else:
        click.echo(format_search_results(results))
        print_success(f"Retrieved {len(results)} rows")


@lookup.command()
@click.argument("lookup_name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--output-file", "-o", help="Output file path.")
@click.pass_context
@handle_cli_errors
def download(
    ctx: click.Context, lookup_name: str, app: str, output_file: str | None
) -> None:
    """Download a lookup file.

    Example:
        splunk-as lookup download users.csv -o users_backup.csv
    """
    client = get_client_from_context(ctx)

    # Validate output file path to prevent directory traversal
    output_file = output_file or lookup_name
    validate_file_path(output_file, "output_file")

    # Validate lookup_name for URL path safety
    safe_lookup_name = validate_path_component(lookup_name, "lookup_name")

    # Stream lookup contents using export endpoint (quote name for defense-in-depth)
    search = f'| inputlookup "{safe_lookup_name}"'
    content = client.post_raw(
        "/search/jobs/oneshot",
        data={
            "search": search,
            "namespace": app,
            "output_mode": "csv",
            "count": 0,  # All rows
        },
        operation="download lookup",
    )

    # Write to file
    with open(output_file, "wb") as f:
        f.write(content)

    print_success(f"Downloaded to {output_file}")


@lookup.command()
@click.argument("file_path")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--name", "-n", help="Lookup name (defaults to filename).")
@click.pass_context
@handle_cli_errors
def upload(ctx: click.Context, file_path: str, app: str, name: str | None) -> None:
    """Upload a lookup file.

    Example:
        splunk-as lookup upload /path/to/users.csv --app search
    """
    # Validate file path to prevent directory traversal
    validate_file_path(file_path, "file_path")

    # Read file content
    with open(file_path, "r") as f:
        content = f.read()

    client = get_client_from_context(ctx)

    lookup_name = name or os.path.basename(file_path)

    # Upload lookup (validates lookup_name and field names internally)
    result = client.upload_lookup(lookup_name, content, app=app)

    print_success(f"Uploaded {file_path} as {lookup_name}")
    if result.get("warning"):
        click.echo(f"Warning: {result['warning']}")


@lookup.command()
@click.argument("lookup_name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def delete(ctx: click.Context, lookup_name: str, app: str, force: bool) -> None:
    """Delete a lookup file.

    Example:
        splunk-as lookup delete old_users.csv --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_lookup_name = validate_path_component(lookup_name, "lookup_name")

    if not force:
        print_warning(f"This will delete lookup file: {lookup_name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_client_from_context(ctx)

    endpoint = f"/servicesNS/-/{safe_app}/data/lookup-table-files/{safe_lookup_name}"
    client.delete(endpoint, operation="delete lookup")

    print_success(f"Deleted lookup file: {lookup_name}")
