"""Saved search commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_as import (
    format_json,
    format_saved_search,
    print_success,
    print_warning,
    validate_path_component,
)

from ..cli_utils import (
    build_endpoint,
    get_client_from_context,
    handle_cli_errors,
    output_results,
)


@click.group()
def savedsearch() -> None:
    """Saved search and report management.

    Create, run, and manage saved searches and reports.
    """
    pass


@savedsearch.command(name="list")
@click.option("--app", "-a", help="Filter by app.")
@click.option("--owner", help="Filter by owner.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_searches(
    ctx: click.Context, app: str | None, owner: str | None, output: str
) -> None:
    """List all saved searches.

    Example:
        splunk-as savedsearch list --app search
    """
    client = get_client_from_context(ctx)
    endpoint = build_endpoint("/saved/searches", app=app, owner=owner)
    response = client.get(endpoint, operation="list saved searches")

    searches = [
        {
            "name": entry.get("name"),
            "app": entry.get("acl", {}).get("app", ""),
            "is_scheduled": entry.get("content", {}).get("is_scheduled", False),
            "disabled": entry.get("content", {}).get("disabled", False),
        }
        for entry in response.get("entry", [])
    ]
    output_results(
        searches, output, success_msg=f"Found {len(searches)} saved searches"
    )


@savedsearch.command()
@click.argument("name")
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
def get(ctx: click.Context, name: str, app: str, output: str) -> None:
    """Get a saved search by name.

    Example:
        splunk-as savedsearch get "My Report" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)
    response = client.get(
        f"/servicesNS/-/{safe_app}/saved/searches/{safe_name}",
        operation="get saved search",
    )

    if "entry" in response and response["entry"]:
        entry = response["entry"][0]
        if output == "json":
            click.echo(format_json(entry))
        else:
            click.echo(format_saved_search(entry))


@savedsearch.command()
@click.option("--name", "-n", required=True, help="Saved search name.")
@click.option("--search", "-s", required=True, help="SPL query.")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--cron", help="Cron schedule (e.g., '0 6 * * *').")
@click.option("--description", help="Description.")
@click.pass_context
@handle_cli_errors
def create(
    ctx: click.Context,
    name: str,
    search: str,
    app: str,
    cron: str | None,
    description: str | None,
) -> None:
    """Create a new saved search.

    Example:
        splunk-as savedsearch create --name "Daily Report" --search "index=main | stats count"
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")

    client = get_client_from_context(ctx)

    data: dict[str, str | bool] = {
        "name": name,
        "search": search,
    }

    if cron:
        data["cron_schedule"] = cron
        data["is_scheduled"] = True

    if description:
        data["description"] = description

    client.post(
        f"/servicesNS/nobody/{safe_app}/saved/searches",
        data=data,
        operation="create saved search",
    )
    print_success(f"Created saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--search", "-s", help="New SPL query.")
@click.option("--cron", help="New cron schedule.")
@click.option("--description", help="New description.")
@click.pass_context
@handle_cli_errors
def update(
    ctx: click.Context,
    name: str,
    app: str,
    search: str | None,
    cron: str | None,
    description: str | None,
) -> None:
    """Update a saved search.

    Example:
        splunk-as savedsearch update "My Report" --search "index=main | stats count by host"
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)

    data = {}
    if search:
        data["search"] = search
    if cron:
        data["cron_schedule"] = cron
    if description:
        data["description"] = description

    if not data:
        click.echo("No updates specified.")
        return

    client.post(
        f"/servicesNS/-/{safe_app}/saved/searches/{safe_name}",
        data=data,
        operation="update saved search",
    )
    print_success(f"Updated saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--wait/--no-wait", default=True, help="Wait for completion.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def run(ctx: click.Context, name: str, app: str, wait: bool, output: str) -> None:
    """Run a saved search.

    Example:
        splunk-as savedsearch run "My Report" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)
    response = client.post(
        f"/servicesNS/-/{safe_app}/saved/searches/{safe_name}/dispatch",
        operation="dispatch saved search",
    )
    sid = response.get("sid")

    if output == "json":
        click.echo(format_json({"sid": sid, "name": name}))
    else:
        print_success(f"Dispatched saved search: {name}")
        click.echo(f"SID: {sid}")


@savedsearch.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def enable(ctx: click.Context, name: str, app: str) -> None:
    """Enable a saved search.

    Example:
        splunk-as savedsearch enable "My Report" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)

    client.post(
        f"/servicesNS/-/{safe_app}/saved/searches/{safe_name}/enable",
        operation="enable saved search",
    )
    print_success(f"Enabled saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def disable(ctx: click.Context, name: str, app: str) -> None:
    """Disable a saved search.

    Example:
        splunk-as savedsearch disable "My Report" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)

    client.post(
        f"/servicesNS/-/{safe_app}/saved/searches/{safe_name}/disable",
        operation="disable saved search",
    )
    print_success(f"Disabled saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def delete(ctx: click.Context, name: str, app: str, force: bool) -> None:
    """Delete a saved search.

    Example:
        splunk-as savedsearch delete "My Report" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    if not force:
        print_warning(f"This will delete saved search: {name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_client_from_context(ctx)

    client.delete(
        f"/servicesNS/-/{safe_app}/saved/searches/{safe_name}",
        operation="delete saved search",
    )
    print_success(f"Deleted saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--count", "-c", type=int, default=10, help="Number of entries to show.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def history(ctx: click.Context, name: str, app: str, count: int, output: str) -> None:
    """View run history of a saved search.

    Shows recent dispatches including status, run time, and result count.

    Example:
        splunk-as savedsearch history "My Report" --app search
    """
    # Validate path components to prevent URL path injection
    safe_app = validate_path_component(app, "app")
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)
    response = client.get(
        f"/servicesNS/-/{safe_app}/saved/searches/{safe_name}/history",
        params={"count": count},
        operation="get saved search history",
    )

    history_entries = []
    for entry in response.get("entry", []):
        content = entry.get("content", {})
        history_entries.append(
            {
                "sid": entry.get("name", ""),
                "dispatchState": content.get("dispatchState", ""),
                "resultCount": int(content.get("resultCount", 0) or 0),
                "runDuration": f"{float(content.get('runDuration', 0) or 0):.2f}s",
                "published": entry.get("published", ""),
            }
        )

    output_results(
        history_entries,
        output,
        success_msg=f"Found {len(history_entries)} history entries",
    )
