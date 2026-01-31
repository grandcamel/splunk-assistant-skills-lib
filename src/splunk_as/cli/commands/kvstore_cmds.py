"""KV Store commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import json
from typing import Any

import click

from splunk_as import format_json, print_success, print_warning, validate_path_component

from ..cli_utils import get_client_from_context, handle_cli_errors, output_results


@click.group()
def kvstore() -> None:
    """Key-Value Store operations.

    Manage KV Store collections and records.
    """
    pass


@kvstore.command(name="list")
@click.option("--app", "-a", default="search", help="App context.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_collections(ctx: click.Context, app: str, output: str) -> None:
    """List all KV Store collections.

    Example:
        splunk-as kvstore list --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")

    client = get_client_from_context(ctx)
    response = client.get(
        f"/servicesNS/-/{safe_app}/storage/collections/config",
        operation="list collections",
    )

    collections = [
        {"name": entry.get("name"), "app": entry.get("acl", {}).get("app", "")}
        for entry in response.get("entry", [])
    ]
    output_results(
        collections, output, success_msg=f"Found {len(collections)} collections"
    )


@kvstore.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def create(ctx: click.Context, name: str, app: str) -> None:
    """Create a new KV Store collection.

    Example:
        splunk-as kvstore create my_collection --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")

    client = get_client_from_context(ctx)
    client.post(
        f"/servicesNS/nobody/{safe_app}/storage/collections/config",
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
def delete(ctx: click.Context, name: str, app: str, force: bool) -> None:
    """Delete a KV Store collection.

    Example:
        splunk-as kvstore delete my_collection --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    if not force:
        print_warning(f"This will delete collection: {name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_client_from_context(ctx)
    client.delete(
        f"/servicesNS/nobody/{safe_app}/storage/collections/config/{safe_name}",
        operation="delete collection",
    )
    print_success(f"Deleted collection: {name}")


@kvstore.command()
@click.argument("collection")
@click.argument("data")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def insert(ctx: click.Context, collection: str, data: str, app: str) -> None:
    """Insert a record into a collection.

    Example:
        splunk-as kvstore insert my_collection '{"name": "test", "value": 123}'
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_collection = validate_path_component(collection, "collection")

    client = get_client_from_context(ctx)

    record = json.loads(data)
    response = client.post(
        f"/servicesNS/nobody/{safe_app}/storage/collections/data/{safe_collection}",
        json_body=record,
        operation="insert record",
    )

    key = response.get("_key", "")
    print_success(f"Inserted record: {key}")


@kvstore.command()
@click.argument("collection")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--query", "-q", help="Query filter (JSON).")
@click.option("--limit", "-l", type=int, default=100, help="Maximum records.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def query(
    ctx: click.Context,
    collection: str,
    app: str,
    query: str | None,
    limit: int,
    output: str,
) -> None:
    """Query records from a collection.

    Example:
        splunk-as kvstore query my_collection --query '{"status": "active"}'
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_collection = validate_path_component(collection, "collection")

    client = get_client_from_context(ctx)
    params: dict[str, Any] = {"limit": limit}
    if query:
        params["query"] = query

    response = client.get(
        f"/servicesNS/nobody/{safe_app}/storage/collections/data/{safe_collection}",
        params=params,
        operation="query records",
    )
    records: list[dict[str, Any]] = response if isinstance(response, list) else []
    output_results(records[:50], output, success_msg=f"Found {len(records)} records")


@kvstore.command()
@click.argument("collection")
@click.argument("key")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def get(ctx: click.Context, collection: str, key: str, app: str) -> None:
    """Get a record by key.

    Example:
        splunk-as kvstore get my_collection record_key_123
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_collection = validate_path_component(collection, "collection")
    safe_key = validate_path_component(key, "key")

    client = get_client_from_context(ctx)
    response = client.get(
        f"/servicesNS/nobody/{safe_app}/storage/collections/data/{safe_collection}/{safe_key}",
        operation="get record",
    )
    click.echo(format_json(response))


@kvstore.command()
@click.argument("collection")
@click.argument("key")
@click.argument("data")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def update(ctx: click.Context, collection: str, key: str, data: str, app: str) -> None:
    """Update a record by key.

    Example:
        splunk-as kvstore update my_collection key123 '{"status": "updated"}'
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_collection = validate_path_component(collection, "collection")
    safe_key = validate_path_component(key, "key")

    client = get_client_from_context(ctx)

    record = json.loads(data)
    client.post(
        f"/servicesNS/nobody/{safe_app}/storage/collections/data/{safe_collection}/{safe_key}",
        json_body=record,
        operation="update record",
    )
    print_success(f"Updated record: {key}")


@kvstore.command("delete-record")
@click.argument("collection")
@click.argument("key")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def delete_record(ctx: click.Context, collection: str, key: str, app: str) -> None:
    """Delete a record by key.

    Example:
        splunk-as kvstore delete-record my_collection key123
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_collection = validate_path_component(collection, "collection")
    safe_key = validate_path_component(key, "key")

    client = get_client_from_context(ctx)

    client.delete(
        f"/servicesNS/nobody/{safe_app}/storage/collections/data/{safe_collection}/{safe_key}",
        operation="delete record",
    )
    print_success(f"Deleted record: {key}")


@kvstore.command()
@click.argument("collection")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def truncate(ctx: click.Context, collection: str, app: str, force: bool) -> None:
    """Delete all records from a collection.

    This removes all data but keeps the collection configuration.

    Example:
        splunk-as kvstore truncate my_collection --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_collection = validate_path_component(collection, "collection")

    if not force:
        print_warning(f"This will delete ALL records from collection: {collection}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_client_from_context(ctx)

    # DELETE on collection data endpoint removes all records
    client.delete(
        f"/servicesNS/nobody/{safe_app}/storage/collections/data/{safe_collection}",
        operation="truncate collection",
    )
    print_success(f"Truncated collection: {collection}")


@kvstore.command("batch-insert")
@click.argument("collection")
@click.argument("file_path")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def batch_insert(ctx: click.Context, collection: str, file_path: str, app: str) -> None:
    """Insert multiple records from a JSON file.

    The file should contain a JSON array of records.

    Example:
        splunk-as kvstore batch-insert my_collection records.json
    """
    from splunk_as import validate_file_path

    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_collection = validate_path_component(collection, "collection")

    # Validate file path to prevent directory traversal
    validate_file_path(file_path, "file_path")

    # Read and parse JSON file
    with open(file_path, "r") as f:
        records = json.load(f)

    if not isinstance(records, list):
        click.echo("Error: File must contain a JSON array of records.")
        return

    client = get_client_from_context(ctx)

    # Use batch save endpoint
    response = client.post(
        f"/servicesNS/nobody/{safe_app}/storage/collections/data/{safe_collection}/batch_save",
        json_body=records,
        operation="batch insert records",
    )

    print_success(f"Inserted {len(records)} records into {collection}")
