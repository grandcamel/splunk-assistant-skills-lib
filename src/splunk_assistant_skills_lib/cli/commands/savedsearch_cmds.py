"""Saved search commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import (
    format_json,
    format_saved_search,
    get_splunk_client,
    print_success,
    print_warning,
)

from ..cli_utils import handle_cli_errors, output_results


@click.group()
def savedsearch():
    """Saved search and report management.

    Create, run, and manage saved searches and reports.
    """
    pass


@savedsearch.command(name="list")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--app", "-a", help="Filter by app.")
@click.option("--owner", help="Filter by owner.")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.pass_context
@handle_cli_errors
def list_searches(ctx, profile, app, owner, output):
    """List all saved searches.

    Example:
        splunk-as savedsearch list --app search
    """
    client = get_splunk_client(profile=profile)

    endpoint = "/saved/searches"
    if app and owner:
        endpoint = f"/servicesNS/{owner}/{app}/saved/searches"
    elif app:
        endpoint = f"/servicesNS/-/{app}/saved/searches"

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
    output_results(searches, output, success_msg=f"Found {len(searches)} saved searches")


@savedsearch.command()
@click.argument("name")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.pass_context
@handle_cli_errors
def get(ctx, name, profile, app, output):
    """Get a saved search by name.

    Example:
        splunk-as savedsearch get "My Report" --app search
    """
    client = get_splunk_client(profile=profile)
    response = client.get(f"/servicesNS/-/{app}/saved/searches/{name}", operation="get saved search")

    if "entry" in response and response["entry"]:
        entry = response["entry"][0]
        if output == "json":
            click.echo(format_json(entry))
        else:
            click.echo(format_saved_search(entry))


@savedsearch.command()
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--name", "-n", required=True, help="Saved search name.")
@click.option("--search", "-s", required=True, help="SPL query.")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--cron", help="Cron schedule (e.g., '0 6 * * *').")
@click.option("--description", help="Description.")
@click.pass_context
@handle_cli_errors
def create(ctx, profile, name, search, app, cron, description):
    """Create a new saved search.

    Example:
        splunk-as savedsearch create --name "Daily Report" --search "index=main | stats count"
    """
    client = get_splunk_client(profile=profile)

    data = {
        "name": name,
        "search": search,
    }

    if cron:
        data["cron_schedule"] = cron
        data["is_scheduled"] = True

    if description:
        data["description"] = description

    client.post(
        f"/servicesNS/nobody/{app}/saved/searches",
        data=data,
        operation="create saved search",
    )
    print_success(f"Created saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--search", "-s", help="New SPL query.")
@click.option("--cron", help="New cron schedule.")
@click.option("--description", help="New description.")
@click.pass_context
@handle_cli_errors
def update(ctx, name, profile, app, search, cron, description):
    """Update a saved search.

    Example:
        splunk-as savedsearch update "My Report" --search "index=main | stats count by host"
    """
    client = get_splunk_client(profile=profile)

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
        f"/servicesNS/-/{app}/saved/searches/{name}",
        data=data,
        operation="update saved search",
    )
    print_success(f"Updated saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--wait/--no-wait", default=True, help="Wait for completion.")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format.")
@click.pass_context
@handle_cli_errors
def run(ctx, name, profile, app, wait, output):
    """Run a saved search.

    Example:
        splunk-as savedsearch run "My Report" --app search
    """
    client = get_splunk_client(profile=profile)
    response = client.post(f"/servicesNS/-/{app}/saved/searches/{name}/dispatch", operation="dispatch saved search")
    sid = response.get("sid")

    if output == "json":
        click.echo(format_json({"sid": sid, "name": name}))
    else:
        print_success(f"Dispatched saved search: {name}")
        click.echo(f"SID: {sid}")


@savedsearch.command()
@click.argument("name")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def enable(ctx, name, profile, app):
    """Enable a saved search.

    Example:
        splunk-as savedsearch enable "My Report" --app search
    """
    client = get_splunk_client(profile=profile)

    client.post(
        f"/servicesNS/-/{app}/saved/searches/{name}/enable",
        operation="enable saved search",
    )
    print_success(f"Enabled saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def disable(ctx, name, profile, app):
    """Disable a saved search.

    Example:
        splunk-as savedsearch disable "My Report" --app search
    """
    client = get_splunk_client(profile=profile)

    client.post(
        f"/servicesNS/-/{app}/saved/searches/{name}/disable",
        operation="disable saved search",
    )
    print_success(f"Disabled saved search: {name}")


@savedsearch.command()
@click.argument("name")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def delete(ctx, name, profile, app, force):
    """Delete a saved search.

    Example:
        splunk-as savedsearch delete "My Report" --app search
    """
    if not force:
        print_warning(f"This will delete saved search: {name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_splunk_client(profile=profile)

    client.delete(
        f"/servicesNS/-/{app}/saved/searches/{name}",
        operation="delete saved search",
    )
    print_success(f"Deleted saved search: {name}")
