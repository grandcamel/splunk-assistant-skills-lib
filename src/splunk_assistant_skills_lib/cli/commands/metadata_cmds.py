"""Metadata commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import (
    validate_index_name,
    validate_path_component,
)

from ..cli_utils import get_client_from_context, handle_cli_errors, output_results


@click.group()
def metadata() -> None:
    """Index, source, and sourcetype discovery.

    Explore and discover metadata about your Splunk environment.
    """
    pass


@metadata.command()
@click.option(
    "--filter", "-f", "filter_pattern", help="Filter indexes by name pattern."
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
def indexes(ctx: click.Context, filter_pattern: str | None, output: str) -> None:
    """List all indexes.

    Example:
        splunk-as metadata indexes
    """
    client = get_client_from_context(ctx)
    response = client.get("/data/indexes", operation="list indexes")

    indexes_list = []
    for entry in response.get("entry", []):
        name = entry.get("name")
        if filter_pattern and filter_pattern.lower() not in name.lower():
            continue
        content = entry.get("content", {})
        indexes_list.append(
            {
                "Index": name,
                "Events": f"{content.get('totalEventCount', 0):,}",
                "Size (MB)": f"{content.get('currentDBSizeMB', 0):.0f}",
                "Disabled": "Yes" if content.get("disabled", False) else "No",
            }
        )

    output_results(
        indexes_list, output, success_msg=f"Found {len(indexes_list)} indexes"
    )


@metadata.command("index-info")
@click.argument("index_name")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def index_info(ctx: click.Context, index_name: str, output: str) -> None:
    """Get detailed information about an index.

    Example:
        splunk-as metadata index-info main
    """
    # Validate index name format and prevent URL path injection
    validate_index_name(index_name)
    safe_index = validate_path_component(index_name, "index_name")

    client = get_client_from_context(ctx)
    response = client.get(f"/data/indexes/{safe_index}", operation="get index info")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})
        if output == "json":
            output_results(content, output)
        else:
            click.echo(f"Index: {index_name}")
            click.echo(f"Total Events: {content.get('totalEventCount', 0):,}")
            click.echo(f"Current Size: {content.get('currentDBSizeMB', 0):.2f} MB")
            click.echo(f"Max Size: {content.get('maxDataSizeMB', 0)} MB")
            click.echo(f"Disabled: {content.get('disabled', False)}")
            click.echo(f"Data Type: {content.get('datatype', 'event')}")


@metadata.command()
@click.argument("metadata_type", type=click.Choice(["hosts", "sources", "sourcetypes"]))
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
    ctx: click.Context,
    metadata_type: str,
    index: str | None,
    earliest: str,
    output: str,
) -> None:
    """Search metadata (hosts, sources, sourcetypes).

    Examples:
        splunk-as metadata search sourcetypes --index main
        splunk-as metadata search hosts
        splunk-as metadata search sources --index main
    """
    client = get_client_from_context(ctx)

    search_spl = f"| metadata type={metadata_type}"
    if index:
        # Validate and quote index name for SPL safety
        validate_index_name(index)
        search_spl += f' index="{index}"'
    search_spl += " | table * | sort -totalCount | head 100"

    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": search_spl,
            "earliest_time": earliest,
            "output_mode": "json",
            "count": 1000,
        },
        operation=f"metadata search {metadata_type}",
    )

    results = response.get("results", [])
    if not results and output != "json":
        click.echo(f"No {metadata_type} found.")
        return

    output_results(
        results[:50], output, success_msg=f"Found {len(results)} {metadata_type}"
    )


@metadata.command()
@click.argument("index_name")
@click.option("--sourcetype", "-s", help="Filter by sourcetype.")
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
def fields(
    ctx: click.Context,
    index_name: str,
    sourcetype: str | None,
    earliest: str,
    output: str,
) -> None:
    """Get field summary for an index.

    Example:
        splunk-as metadata fields main --sourcetype access_combined
    """
    client = get_client_from_context(ctx)

    # Validate and quote values for SPL safety
    validate_index_name(index_name)
    search = f'index="{index_name}"'
    if sourcetype:
        # Escape any double quotes in sourcetype
        safe_sourcetype = sourcetype.replace('"', '\\"')
        search += f' sourcetype="{safe_sourcetype}"'
    search += " | fieldsummary | sort -count | head 50"

    response = client.post(
        "/search/jobs/oneshot",
        data={
            "search": search,
            "earliest_time": earliest,
            "output_mode": "json",
            "count": 100,
        },
        operation="get field summary",
    )

    results = response.get("results", [])
    if not results and output != "json":
        click.echo("No fields found.")
        return

    display_data = [
        {
            "Field": r.get("field", ""),
            "Count": f"{int(r.get('count', 0)):,}",
            "Distinct": r.get("distinct_count", ""),
        }
        for r in results
    ]
    output_results(display_data, output, success_msg=f"Found {len(results)} fields")


# Aliases for backward compatibility
@metadata.command()
@click.option("--index", "-i", help="Filter by index.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def sourcetypes(ctx: click.Context, index: str | None, output: str) -> None:
    """List sourcetypes. Alias for 'metadata search sourcetypes'."""
    ctx.invoke(search, metadata_type="sourcetypes", index=index, output=output)


@metadata.command()
@click.option("--index", "-i", help="Filter by index.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def sources(ctx: click.Context, index: str | None, output: str) -> None:
    """List sources. Alias for 'metadata search sources'."""
    ctx.invoke(search, metadata_type="sources", index=index, output=output)
