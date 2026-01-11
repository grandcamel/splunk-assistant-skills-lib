"""Metadata commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import get_splunk_client

from ..cli_utils import handle_cli_errors, output_results


@click.group()
def metadata():
    """Index, source, and sourcetype discovery.

    Explore and discover metadata about your Splunk environment.
    """
    pass


@metadata.command()
@click.option("--filter", "-f", "filter_pattern", help="Filter indexes by name pattern.")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def indexes(ctx, filter_pattern, output):
    """List all indexes.

    Example:
        splunk-as metadata indexes
    """
    client = get_splunk_client()
    response = client.get("/data/indexes", operation="list indexes")

    indexes_list = []
    for entry in response.get("entry", []):
        name = entry.get("name")
        if filter_pattern and filter_pattern.lower() not in name.lower():
            continue
        content = entry.get("content", {})
        indexes_list.append({
            "Index": name,
            "Events": f"{content.get('totalEventCount', 0):,}",
            "Size (MB)": f"{content.get('currentDBSizeMB', 0):.0f}",
            "Disabled": "Yes" if content.get("disabled", False) else "No",
        })

    output_results(indexes_list, output, success_msg=f"Found {len(indexes_list)} indexes")


@metadata.command("index-info")
@click.argument("index_name")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def index_info(ctx, index_name, output):
    """Get detailed information about an index.

    Example:
        splunk-as metadata index-info main
    """
    client = get_splunk_client()
    response = client.get(f"/data/indexes/{index_name}", operation="get index info")

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
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def search(ctx, metadata_type, index, earliest, output):
    """Search metadata (hosts, sources, sourcetypes).

    Examples:
        splunk-as metadata search sourcetypes --index main
        splunk-as metadata search hosts
        splunk-as metadata search sources --index main
    """
    client = get_splunk_client()

    search_spl = f"| metadata type={metadata_type}"
    if index:
        search_spl += f" index={index}"
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

    output_results(results[:50], output, success_msg=f"Found {len(results)} {metadata_type}")


@metadata.command()
@click.argument("index_name")
@click.option("--sourcetype", "-s", help="Filter by sourcetype.")
@click.option("--earliest", "-e", default="-24h", help="Earliest time.")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def fields(ctx, index_name, sourcetype, earliest, output):
    """Get field summary for an index.

    Example:
        splunk-as metadata fields main --sourcetype access_combined
    """
    client = get_splunk_client()

    search = f"index={index_name}"
    if sourcetype:
        search += f" sourcetype={sourcetype}"
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
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def sourcetypes(ctx, index, output):
    """List sourcetypes. Alias for 'metadata search sourcetypes'."""
    ctx.invoke(search, metadata_type="sourcetypes", index=index, output=output)


@metadata.command()
@click.option("--index", "-i", help="Filter by index.")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def sources(ctx, index, output):
    """List sources. Alias for 'metadata search sources'."""
    ctx.invoke(search, metadata_type="sources", index=index, output=output)
