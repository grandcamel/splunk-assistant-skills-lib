"""App commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

from typing import Any

import click

from splunk_as import (
    format_json,
    format_table,
    print_success,
    print_warning,
    validate_path_component,
)

from ..cli_utils import get_client_from_context, handle_cli_errors


@click.group()
def app() -> None:
    """Application management.

    List, install, and manage Splunk apps.
    """
    pass


@app.command(name="list")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_apps(ctx: click.Context, output: str) -> None:
    """List all installed apps.

    Example:
        splunk-as app list
    """
    client = get_client_from_context(ctx)
    response = client.get("/apps/local", operation="list apps")

    apps = []
    for entry in response.get("entry", []):
        content = entry.get("content", {})
        apps.append(
            {
                "name": entry.get("name"),
                "label": content.get("label", ""),
                "version": content.get("version", ""),
                "disabled": content.get("disabled", False),
                "visible": content.get("visible", True),
            }
        )

    if output == "json":
        click.echo(format_json(apps))
    else:
        click.echo(format_table(apps))
        print_success(f"Found {len(apps)} apps")


@app.command()
@click.argument("name")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def get(ctx: click.Context, name: str, output: str) -> None:
    """Get app details.

    Example:
        splunk-as app get search
    """
    # Validate name to prevent URL path injection
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)
    response = client.get(f"/apps/local/{safe_name}", operation="get app")

    if "entry" in response and response["entry"]:
        entry = response["entry"][0]
        content = entry.get("content", {})

        if output == "json":
            click.echo(format_json(entry))
        else:
            click.echo(f"Name: {entry.get('name')}")
            click.echo(f"Label: {content.get('label', '')}")
            click.echo(f"Version: {content.get('version', '')}")
            click.echo(f"Author: {content.get('author', '')}")
            click.echo(f"Description: {content.get('description', '')[:100]}")
            click.echo(f"Disabled: {content.get('disabled', False)}")
            click.echo(f"Visible: {content.get('visible', True)}")


@app.command()
@click.argument("name")
@click.pass_context
@handle_cli_errors
def enable(ctx: click.Context, name: str) -> None:
    """Enable an app.

    Example:
        splunk-as app enable my_app
    """
    # Validate name to prevent URL path injection
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)
    client.post(
        f"/apps/local/{safe_name}/enable",
        operation="enable app",
    )
    print_success(f"Enabled app: {name}")


@app.command()
@click.argument("name")
@click.pass_context
@handle_cli_errors
def disable(ctx: click.Context, name: str) -> None:
    """Disable an app.

    Example:
        splunk-as app disable my_app
    """
    # Validate name to prevent URL path injection
    safe_name = validate_path_component(name, "name")

    client = get_client_from_context(ctx)
    client.post(
        f"/apps/local/{safe_name}/disable",
        operation="disable app",
    )
    print_success(f"Disabled app: {name}")


@app.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def uninstall(ctx: click.Context, name: str, force: bool) -> None:
    """Uninstall an app.

    Example:
        splunk-as app uninstall my_app
    """
    # Validate name to prevent URL path injection
    safe_name = validate_path_component(name, "name")

    if not force:
        print_warning(f"This will uninstall app: {name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_client_from_context(ctx)
    client.delete(f"/apps/local/{safe_name}", operation="uninstall app")
    print_success(f"Uninstalled app: {name}")


@app.command()
@click.argument("package_path")
@click.option("--name", "-n", help="App name (if different from package).")
@click.option("--update/--no-update", default=False, help="Update if exists.")
@click.pass_context
@handle_cli_errors
def install(
    ctx: click.Context, package_path: str, name: str | None, update: bool
) -> None:
    """Install an app from a package.

    Example:
        splunk-as app install /path/to/app.tar.gz
    """
    client = get_client_from_context(ctx)

    data: dict[str, Any] = {"name": package_path}
    if name:
        data["name"] = name
    if update:
        data["update"] = True

    # Note: This requires uploading the file - simplified version
    click.echo(f"Installing app from: {package_path}")
    click.echo("Note: Use Splunk Web or CLI for full package installation.")
    print_warning("Direct package upload not yet implemented in this CLI.")
