"""Security commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import (
    format_json,
    get_splunk_client,
    print_error,
    print_success,
)

from ..cli_utils import handle_cli_errors, output_results


@click.group()
def security():
    """Token management and RBAC.

    Manage authentication tokens, users, and permissions.
    """
    pass


@security.command()
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def whoami(ctx, profile, output):
    """Get current user information.

    Example:
        splunk-as security whoami
    """
    client = get_splunk_client(profile=profile)
    response = client.get("/authentication/current-context", operation="whoami")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})

        if output == "json":
            click.echo(format_json(content))
        else:
            click.echo(f"Username: {content.get('username', 'Unknown')}")
            click.echo(f"Real Name: {content.get('realname', '')}")
            click.echo(f"Roles: {', '.join(content.get('roles', []))}")
            click.echo(f"Email: {content.get('email', '')}")


@security.command(name="list-tokens")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def list_tokens(ctx, profile, output):
    """List authentication tokens.

    Example:
        splunk-as security list-tokens
    """
    client = get_splunk_client(profile=profile)
    response = client.get("/authorization/tokens", operation="list tokens")

    tokens = [
        {
            "id": entry.get("name"),
            "status": entry.get("content", {}).get("status", ""),
            "expires": entry.get("content", {}).get("expiresOn", "Never"),
            "audience": entry.get("content", {}).get("audience", ""),
        }
        for entry in response.get("entry", [])
    ]
    output_results(tokens, output, success_msg=f"Found {len(tokens)} tokens")


@security.command(name="create-token")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option("--name", "-n", required=True, help="Token name.")
@click.option("--audience", help="Token audience.")
@click.option("--expires", type=int, help="Expiration time in seconds.")
@click.pass_context
@handle_cli_errors
def create_token(ctx, profile, name, audience, expires):
    """Create a new authentication token.

    Example:
        splunk-as security create-token --name "API Token" --expires 86400
    """
    client = get_splunk_client(profile=profile)

    data = {"name": name}
    if audience:
        data["audience"] = audience
    if expires:
        data["expiresOn"] = f"+{expires}s"

    response = client.post("/authorization/tokens", data=data, operation="create token")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})
        token = content.get("token", "")

        click.echo(f"Token created: {name}")
        click.echo(f"Token value: {token}")
        click.echo("\nSave this token - it won't be shown again!")


@security.command(name="delete-token")
@click.argument("token_id")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.pass_context
@handle_cli_errors
def delete_token(ctx, token_id, profile):
    """Delete an authentication token.

    Example:
        splunk-as security delete-token token_12345
    """
    client = get_splunk_client(profile=profile)
    client.delete(f"/authorization/tokens/{token_id}", operation="delete token")
    print_success(f"Deleted token: {token_id}")


@security.command(name="list-users")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def list_users(ctx, profile, output):
    """List all users.

    Example:
        splunk-as security list-users
    """
    client = get_splunk_client(profile=profile)
    response = client.get("/authentication/users", operation="list users")

    users = [
        {
            "name": entry.get("name"),
            "realname": entry.get("content", {}).get("realname", ""),
            "roles": ", ".join(entry.get("content", {}).get("roles", [])),
        }
        for entry in response.get("entry", [])
    ]
    output_results(users, output, success_msg=f"Found {len(users)} users")


@security.command(name="list-roles")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option(
    "--output", "-o", type=click.Choice(["text", "json"]), default="text", help="Output format."
)
@click.pass_context
@handle_cli_errors
def list_roles(ctx, profile, output):
    """List all roles.

    Example:
        splunk-as security list-roles
    """
    client = get_splunk_client(profile=profile)
    response = client.get("/authorization/roles", operation="list roles")

    roles = [
        {
            "name": entry.get("name"),
            "imported_roles": ", ".join(entry.get("content", {}).get("imported_roles", [])),
        }
        for entry in response.get("entry", [])
    ]
    output_results(roles, output, success_msg=f"Found {len(roles)} roles")


@security.command()
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def capabilities(ctx, profile, output):
    """Get current user capabilities.

    Example:
        splunk-as security capabilities
    """
    client = get_splunk_client(profile=profile)
    response = client.get("/authentication/current-context", operation="get capabilities")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})
        caps = content.get("capabilities", [])

        if output == "json":
            click.echo(format_json(caps))
        else:
            click.echo(f"Capabilities ({len(caps)}):")
            for cap in sorted(caps):
                click.echo(f"  - {cap}")


@security.command()
@click.argument("path")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def acl(ctx, path, profile, output):
    """Get ACL for a resource.

    Example:
        splunk-as security acl /servicesNS/admin/search/saved/searches/MySavedSearch
    """
    client = get_splunk_client(profile=profile)
    response = client.get(f"{path}/acl", operation="get ACL")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})

        if output == "json":
            click.echo(format_json(content))
        else:
            click.echo(f"Owner: {content.get('owner', 'Unknown')}")
            click.echo(f"App: {content.get('app', 'Unknown')}")
            click.echo(f"Sharing: {content.get('sharing', 'Unknown')}")
            click.echo(f"Modifiable: {content.get('modifiable', False)}")
            if "perms" in content:
                perms = content["perms"]
                click.echo(f"Read: {', '.join(perms.get('read', []))}")
                click.echo(f"Write: {', '.join(perms.get('write', []))}")


@security.command()
@click.argument("capability")
@click.option("--profile", "-p", help="Splunk profile to use.")
@click.pass_context
@handle_cli_errors
def check(ctx, capability, profile):
    """Check if current user has a capability.

    Example:
        splunk-as security check admin_all_objects
    """
    client = get_splunk_client(profile=profile)
    response = client.get("/authentication/current-context", operation="check capability")

    if "entry" in response and response["entry"]:
        content = response["entry"][0].get("content", {})
        caps = content.get("capabilities", [])

        if capability in caps:
            print_success(f"You have capability: {capability}")
        else:
            print_error(f"You do NOT have capability: {capability}")
