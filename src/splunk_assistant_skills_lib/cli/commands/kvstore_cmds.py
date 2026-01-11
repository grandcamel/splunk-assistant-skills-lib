"""KV Store commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import json

import click

from splunk_assistant_skills_lib import format_json, get_splunk_client, print_success, print_warning

from ..cli_utils import handle_cli_errors, output_results


@click.group()
def kvstore():
    """Key-Value Store operations.

    Manage KV Store collections and records.
    """
    pass


@kvstore.command(name="list")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.pass_context
@handle_cli_errors
def list_collections(ctx, app, output):
    """List all KV Store collections.

    Example:
        splunk-as kvstore list --app search
    """
    client = get_splunk_client()
    response = client.get(f"/servicesNS/-/{app}/storage/collections/config", operation="list collections")

    collections = [
        {"name": entry.get("name"), "app": entry.get("acl", {}).get("app", "")}
        for entry in response.get("entry", [])
    ]
    output_results(collections, output, success_msg=f"Found {len(collections)} collections")


@kvstore.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def create(ctx, name, app):
    """Create a new KV Store collection.

    Example:
        splunk-as kvstore create my_collection --app search
    """
    client = get_splunk_client()
    client.post(
        f"/servicesNS/nobody/{app}/storage/collections/config",
        data={"name": name},
        operation="create collection",
    )
    print_success(f"Created collection: {name}")


@kvstore.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def delete(ctx, name, app, force):
    """Delete a KV Store collection.

    Example:
        splunk-as kvstore delete my_collection --app search
    """
    if not force:
        print_warning(f"This will delete collection: {name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_splunk_client()
    client.delete(
        f"/servicesNS/nobody/{app}/storage/collections/config/{name}",
        operation="delete collection",
    )
    print_success(f"Deleted collection: {name}")


@kvstore.command()
@click.argument("collection")
@click.argument("data")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def insert(ctx, collection, data, app):
    """Insert a record into a collection.

    Example:
        splunk-as kvstore insert my_collection '{"name": "test", "value": 123}'
    """
    client = get_splunk_client()

    record = json.loads(data)
    response = client.post(
        f"/servicesNS/nobody/{app}/storage/collections/data/{collection}",
        json=record,
        operation="insert record",
    )

    key = response.get("_key", "")
    print_success(f"Inserted record: {key}")


@kvstore.command()
@click.argument("collection")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--query", "-q", help="Query filter (JSON).")
@click.option("--limit", "-l", type=int, default=100, help="Maximum records.")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.pass_context
@handle_cli_errors
def query(ctx, collection, app, query, limit, output):
    """Query records from a collection.

    Example:
        splunk-as kvstore query my_collection --query '{"status": "active"}'
    """
    client = get_splunk_client()
    params = {"limit": limit}
    if query:
        params["query"] = query

    response = client.get(f"/servicesNS/nobody/{app}/storage/collections/data/{collection}", params=params, operation="query records")
    records = response if isinstance(response, list) else []
    output_results(records[:50], output, success_msg=f"Found {len(records)} records")


@kvstore.command()
@click.argument("collection")
@click.argument("key")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def get(ctx, collection, key, app):
    """Get a record by key.

    Example:
        splunk-as kvstore get my_collection record_key_123
    """
    client = get_splunk_client()
    response = client.get(f"/servicesNS/nobody/{app}/storage/collections/data/{collection}/{key}", operation="get record")
    click.echo(format_json(response))


@kvstore.command()
@click.argument("collection")
@click.argument("key")
@click.argument("data")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def update(ctx, collection, key, data, app):
    """Update a record by key.

    Example:
        splunk-as kvstore update my_collection key123 '{"status": "updated"}'
    """
    client = get_splunk_client()

    record = json.loads(data)
    client.post(
        f"/servicesNS/nobody/{app}/storage/collections/data/{collection}/{key}",
        json=record,
        operation="update record",
    )
    print_success(f"Updated record: {key}")


@kvstore.command("delete-record")
@click.argument("collection")
@click.argument("key")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def delete_record(ctx, collection, key, app):
    """Delete a record by key.

    Example:
        splunk-as kvstore delete-record my_collection key123
    """
    client = get_splunk_client()

    client.delete(
        f"/servicesNS/nobody/{app}/storage/collections/data/{collection}/{key}",
        operation="delete record",
    )
    print_success(f"Deleted record: {key}")
