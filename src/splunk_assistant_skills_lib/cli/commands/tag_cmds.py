"""Tag commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import (
    format_json,
    format_table,
    get_splunk_client,
    print_success,
)

from ..cli_utils import handle_cli_errors


@click.group()
def tag():
    """Knowledge object tagging.

    Manage tags on Splunk knowledge objects.
    """
    pass


@tag.command(name="list")
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
def list_tags(ctx, app, output):
    """List all tags.

    Example:
        splunk-as tag list --app search
    """
    client = get_splunk_client()

    # Use a search to find tags
    search = "| rest /services/configs/conf-tags | table title, eai:acl.app"
    response = client.post(
        "/search/jobs/oneshot",
        data={"search": search, "output_mode": "json", "count": 1000},
        operation="list tags",
    )

    results = response.get("results", [])

    if app:
        results = [r for r in results if r.get("eai:acl.app") == app]

    if output == "json":
        click.echo(format_json(results))
    else:
        if not results:
            click.echo("No tags found.")
            return

        display_data = []
        for r in results:
            display_data.append(
                {
                    "Tag": r.get("title", ""),
                    "App": r.get("eai:acl.app", ""),
                }
            )
        click.echo(format_table(display_data))
        print_success(f"Found {len(results)} tags")


@tag.command()
@click.argument("field_value_pair")
@click.argument("tag_name")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def add(ctx, field_value_pair, tag_name, app):
    """Add a tag to a field value.

    Example:
        splunk-as tag add "host::webserver01" "production" --app search
    """
    client = get_splunk_client()

    # Parse field::value
    if "::" not in field_value_pair:
        click.echo("Error: field_value_pair must be in format 'field::value'")
        return

    field, value = field_value_pair.split("::", 1)

    # Create the tag
    data = {
        "name": f"{field}::{value}",
        tag_name: "enabled",
    }

    client.post(
        f"/servicesNS/nobody/{app}/configs/conf-tags",
        data=data,
        operation="add tag",
    )
    print_success(f"Added tag '{tag_name}' to {field}::{value}")


@tag.command()
@click.argument("field_value_pair")
@click.argument("tag_name")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def remove(ctx, field_value_pair, tag_name, app):
    """Remove a tag from a field value.

    Example:
        splunk-as tag remove "host::webserver01" "production" --app search
    """
    client = get_splunk_client()

    # Parse field::value
    if "::" not in field_value_pair:
        click.echo("Error: field_value_pair must be in format 'field::value'")
        return

    field, value = field_value_pair.split("::", 1)

    # Disable the tag
    data = {tag_name: "disabled"}

    client.post(
        f"/servicesNS/nobody/{app}/configs/conf-tags/{field}%3A%3A{value}",
        data=data,
        operation="remove tag",
    )
    print_success(f"Removed tag '{tag_name}' from {field}::{value}")


@tag.command()
@click.argument("tag_name")
@click.option("--index", "-i", help="Filter by index.")
@click.option("--earliest", "-e", default="-24h", help="Earliest time.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def search(ctx, tag_name, index, earliest, output):
    """Search for events with a specific tag.

    Example:
        splunk-as tag search "production" --index main
    """
    client = get_splunk_client()

    spl = f"tag={tag_name}"
    if index:
        spl = f"index={index} {spl}"
    spl += " | head 100"

    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": spl,
            "earliest_time": earliest,
            "output_mode": "json",
            "count": 100,
        },
        operation="search by tag",
    )

    results = response.get("results", [])

    if output == "json":
        click.echo(format_json(results))
    else:
        if not results:
            click.echo(f"No events found with tag: {tag_name}")
            return

        click.echo(format_table(results[:20]))
        print_success(f"Found {len(results)} events with tag '{tag_name}'")
