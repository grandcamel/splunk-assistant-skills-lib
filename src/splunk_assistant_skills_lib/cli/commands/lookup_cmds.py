"""Lookup commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import os

import click

from splunk_assistant_skills_lib import (
    format_json,
    format_search_results,
    format_table,
    get_splunk_client,
    print_success,
    print_warning,
)

from ..cli_utils import handle_cli_errors


@click.group()
def lookup():
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
def list_lookups(ctx, app, output):
    """List all lookup files.

    Example:
        splunk-as lookup list --app search
    """
    client = get_splunk_client()

    endpoint = "/data/lookup-table-files"
    if app:
        endpoint = f"/servicesNS/-/{app}/data/lookup-table-files"

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
def get(ctx, lookup_name, app, output, count):
    """Get contents of a lookup file.

    Example:
        splunk-as lookup get users.csv --app search
    """
    client = get_splunk_client()

    # Use inputlookup to get contents
    search = f"| inputlookup {lookup_name} | head {count}"
    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": search,
            "namespace": app,
            "output_mode": "json",
            "count": count,
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
def download(ctx, lookup_name, app, output_file):
    """Download a lookup file.

    Example:
        splunk-as lookup download users.csv -o users_backup.csv
    """
    client = get_splunk_client()

    output_file = output_file or lookup_name

    # Stream lookup contents using export endpoint
    search = f"| inputlookup {lookup_name}"
    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": search,
            "namespace": app,
            "output_mode": "csv",
            "count": 0,  # All rows
        },
        operation="download lookup",
        raw_response=True,
    )

    # Write to file
    with open(output_file, "wb") as f:
        if hasattr(response, "content"):
            f.write(response.content)
        else:
            f.write(str(response).encode())

    print_success(f"Downloaded to {output_file}")


@lookup.command()
@click.argument("file_path")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--name", "-n", help="Lookup name (defaults to filename).")
@click.pass_context
@handle_cli_errors
def upload(ctx, file_path, app, name):
    """Upload a lookup file.

    Example:
        splunk-as lookup upload /path/to/users.csv --app search
    """
    client = get_splunk_client()

    lookup_name = name or os.path.basename(file_path)

    # Upload using multipart form
    client.upload_lookup(file_path, lookup_name, app=app)

    print_success(f"Uploaded {file_path} as {lookup_name}")


@lookup.command()
@click.argument("lookup_name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def delete(ctx, lookup_name, app, force):
    """Delete a lookup file.

    Example:
        splunk-as lookup delete old_users.csv --app search
    """
    if not force:
        print_warning(f"This will delete lookup file: {lookup_name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_splunk_client()

    endpoint = f"/servicesNS/-/{app}/data/lookup-table-files/{lookup_name}"
    client.delete(endpoint, operation="delete lookup")

    print_success(f"Deleted lookup file: {lookup_name}")
