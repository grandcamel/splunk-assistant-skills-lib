"""Tag commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_as import (
    format_json,
    format_table,
    print_success,
    quote_field_value,
    validate_index_name,
    validate_path_component,
)

from ..cli_utils import get_client_from_context, handle_cli_errors


@click.group()
def tag() -> None:
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
def list_tags(ctx: click.Context, app: str | None, output: str) -> None:
    """List all tags.

    Example:
        splunk-as tag list --app search
    """
    client = get_client_from_context(ctx)

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
def add(ctx: click.Context, field_value_pair: str, tag_name: str, app: str) -> None:
    """Add a tag to a field value.

    Example:
        splunk-as tag add "host::webserver01" "production" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")

    client = get_client_from_context(ctx)

    # Parse field::value
    if "::" not in field_value_pair:
        click.echo("Error: field_value_pair must be in format 'field::value'")
        return

    field, value = field_value_pair.split("::", 1)

    # Validate field, value, and tag_name to prevent injection
    safe_field = validate_path_component(field, "field")
    safe_value = validate_path_component(value, "value")
    safe_tag_name = validate_path_component(tag_name, "tag_name")

    # Create the tag
    data = {
        "name": f"{safe_field}::{safe_value}",
        safe_tag_name: "enabled",
    }

    client.post(
        f"/servicesNS/nobody/{safe_app}/configs/conf-tags",
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
def remove(ctx: click.Context, field_value_pair: str, tag_name: str, app: str) -> None:
    """Remove a tag from a field value.

    Example:
        splunk-as tag remove "host::webserver01" "production" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")

    client = get_client_from_context(ctx)

    # Parse field::value
    if "::" not in field_value_pair:
        click.echo("Error: field_value_pair must be in format 'field::value'")
        return

    field, value = field_value_pair.split("::", 1)

    # Validate field, value, and tag_name to prevent injection
    safe_field = validate_path_component(field, "field")
    safe_value = validate_path_component(value, "value")
    safe_tag_name = validate_path_component(tag_name, "tag_name")

    # Disable the tag
    # Note: The stanza name is field::value - we need to URL-encode :: as part of the path
    # validate_path_component already URL-encodes the individual components
    from urllib.parse import quote

    stanza_name = quote(f"{field}::{value}", safe="")
    data = {safe_tag_name: "disabled"}

    client.post(
        f"/servicesNS/nobody/{safe_app}/configs/conf-tags/{stanza_name}",
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
def search(
    ctx: click.Context, tag_name: str, index: str | None, earliest: str, output: str
) -> None:
    """Search for events with a specific tag.

    Example:
        splunk-as tag search "production" --index main
    """
    client = get_client_from_context(ctx)

    # Quote tag_name to prevent SPL injection
    spl = f"tag={quote_field_value(tag_name)}"
    if index:
        # Validate index name format
        validate_index_name(index)
        spl = f'index="{index}" {spl}'
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
