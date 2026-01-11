"""Admin commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import json

import click

from splunk_assistant_skills_lib import format_json, get_splunk_client, print_success

from ..cli_utils import build_endpoint, handle_cli_errors, output_results


@click.group()
def admin():
    """Server administration and REST API access.

    Check server status, health, and make generic REST calls.
    """
    pass


@admin.command()
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def info(ctx, output):
    """Get server information.

    Example:
        splunk-as admin info
    """
    client = get_splunk_client()
    response = client.get("/server/info", operation="get server info")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})

        if output == "json":
            click.echo(format_json(content))
        else:
            click.echo(f"Server: {content.get('serverName', 'Unknown')}")
            click.echo(f"Version: {content.get('version', 'Unknown')}")
            click.echo(f"Build: {content.get('build', 'Unknown')}")
            click.echo(f"OS: {content.get('os_name', 'Unknown')}")
            click.echo(f"CPU Arch: {content.get('cpu_arch', 'Unknown')}")
            click.echo(f"License: {content.get('licenseState', 'Unknown')}")


@admin.command()
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def status(ctx, output):
    """Get server status.

    Example:
        splunk-as admin status
    """
    client = get_splunk_client()
    response = client.get("/server/status", operation="get server status")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})
        if output == "json":
            click.echo(format_json(content))
        else:
            click.echo(f"Status: {content.get('status', 'Unknown')}")


@admin.command()
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def health(ctx, output):
    """Get server health status.

    Example:
        splunk-as admin health
    """
    client = get_splunk_client()
    response = client.get("/server/health/splunkd", operation="get health")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})
        if output == "json":
            click.echo(format_json(content))
        else:
            click.echo(f"Health: {content.get('health', 'Unknown')}")
            for feature, feat_status in content.get("features", {}).items():
                click.echo(f"  {feature}: {feat_status.get('health', 'Unknown')}")


@admin.command(name="list-users")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_users(ctx, output):
    """List all users.

    Example:
        splunk-as admin list-users
    """
    client = get_splunk_client()
    response = client.get("/authentication/users", operation="list users")

    users = [
        {
            "name": entry.get("name"),
            "realname": entry.get("content", {}).get("realname", ""),
            "roles": ", ".join(entry.get("content", {}).get("roles", [])),
            "email": entry.get("content", {}).get("email", ""),
        }
        for entry in response.get("entry", [])
    ]
    output_results(users, output, success_msg=f"Found {len(users)} users")


@admin.command(name="list-roles")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_roles(ctx, output):
    """List all roles.

    Example:
        splunk-as admin list-roles
    """
    client = get_splunk_client()
    response = client.get("/authorization/roles", operation="list roles")

    roles = [
        {
            "name": entry.get("name"),
            "imported_roles": ", ".join(
                entry.get("content", {}).get("imported_roles", [])
            ),
            "capabilities_count": len(entry.get("content", {}).get("capabilities", [])),
        }
        for entry in response.get("entry", [])
    ]
    output_results(roles, output, success_msg=f"Found {len(roles)} roles")


@admin.command("rest-get")
@click.argument("endpoint")
@click.option("--app", "-a", help="App context.")
@click.option("--owner", help="Owner context.")
@click.pass_context
@handle_cli_errors
def rest_get(ctx, endpoint, app, owner):
    """Make a GET request to a REST endpoint.

    Example:
        splunk-as admin rest-get /services/server/info
    """
    client = get_splunk_client()
    endpoint = build_endpoint(endpoint, app=app, owner=owner)
    response = client.get(endpoint, operation=f"GET {endpoint}")
    click.echo(format_json(response))


@admin.command("rest-post")
@click.argument("endpoint")
@click.option("--data", "-d", help="POST data (JSON or key=value pairs).")
@click.option("--app", "-a", help="App context.")
@click.option("--owner", help="Owner context.")
@click.pass_context
@handle_cli_errors
def rest_post(ctx, endpoint, data, app, owner):
    """Make a POST request to a REST endpoint.

    Example:
        splunk-as admin rest-post /services/saved/searches -d '{"name": "test"}'
    """
    client = get_splunk_client()
    endpoint = build_endpoint(endpoint, app=app, owner=owner)

    post_data = None
    if data:
        try:
            post_data = json.loads(data)
        except json.JSONDecodeError:
            post_data = dict(
                item.split("=", 1) for item in data.split("&") if "=" in item
            )

    response = client.post(endpoint, data=post_data, operation=f"POST {endpoint}")
    click.echo(format_json(response))
