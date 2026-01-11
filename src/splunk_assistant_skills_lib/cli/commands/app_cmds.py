"""App commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import (
    format_json,
    format_table,
    get_splunk_client,
    print_success,
    print_warning,
)

from ..cli_utils import handle_cli_errors


@click.group()
def app():
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
def list_apps(ctx, profile, output):
    """List all installed apps.

    Example:
        splunk-as app list
    """
    client = get_splunk_client(profile=profile)
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
def get(ctx, name, profile, output):
    """Get app details.

    Example:
        splunk-as app get search
    """
    client = get_splunk_client(profile=profile)
    response = client.get(f"/apps/local/{name}", operation="get app")

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
def enable(ctx, name, profile):
    """Enable an app.

    Example:
        splunk-as app enable my_app
    """
    client = get_splunk_client(profile=profile)
    client.post(
        f"/apps/local/{name}/enable",
        operation="enable app",
    )
    print_success(f"Enabled app: {name}")


@app.command()
@click.argument("name")
@click.pass_context
@handle_cli_errors
def disable(ctx, name, profile):
    """Disable an app.

    Example:
        splunk-as app disable my_app
    """
    client = get_splunk_client(profile=profile)
    client.post(
        f"/apps/local/{name}/disable",
        operation="disable app",
    )
    print_success(f"Disabled app: {name}")


@app.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation.")
@click.pass_context
@handle_cli_errors
def uninstall(ctx, name, profile, force):
    """Uninstall an app.

    Example:
        splunk-as app uninstall my_app
    """
    if not force:
        print_warning(f"This will uninstall app: {name}")
        if not click.confirm("Are you sure?"):
            click.echo("Cancelled.")
            return

    client = get_splunk_client(profile=profile)
    client.delete(f"/apps/local/{name}", operation="uninstall app")
    print_success(f"Uninstalled app: {name}")


@app.command()
@click.argument("package_path")
@click.option("--name", "-n", help="App name (if different from package).")
@click.option("--update/--no-update", default=False, help="Update if exists.")
@click.pass_context
@handle_cli_errors
def install(ctx, package_path, profile, name, update):
    """Install an app from a package.

    Example:
        splunk-as app install /path/to/app.tar.gz
    """
    client = get_splunk_client(profile=profile)

    data = {"name": package_path}
    if name:
        data["name"] = name
    if update:
        data["update"] = True

    # Note: This requires uploading the file - simplified version
    click.echo(f"Installing app from: {package_path}")
    click.echo("Note: Use Splunk Web or CLI for full package installation.")
    print_warning("Direct package upload not yet implemented in this CLI.")
