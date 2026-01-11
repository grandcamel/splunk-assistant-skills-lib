"""Alert commands for Splunk Assistant Skills CLI."""

from __future__ import annotations

import click

from splunk_assistant_skills_lib import format_json, get_splunk_client, print_success

from ..cli_utils import build_endpoint, handle_cli_errors, output_results


@click.group()
def alert():
    """Alert management and monitoring.

    Monitor and manage Splunk alerts.
    """
    pass


@alert.command(name="list")
@click.option("--app", "-a", help="Filter by app.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def list_alerts(ctx, app, output):
    """List all alerts (scheduled searches with alert actions).

    Example:
        splunk-as alert list --app search
    """
    client = get_splunk_client()
    endpoint = build_endpoint("/saved/searches", app=app)
    response = client.get(
        endpoint,
        params={"search": "is_scheduled=1 AND alert.track=1"},
        operation="list alerts",
    )

    alerts = [
        {
            "name": entry.get("name"),
            "app": entry.get("acl", {}).get("app", ""),
            "disabled": entry.get("content", {}).get("disabled", False),
            "alert_type": entry.get("content", {}).get("alert_type", ""),
        }
        for entry in response.get("entry", [])
    ]
    output_results(alerts, output, success_msg=f"Found {len(alerts)} alerts")


@alert.command()
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
def get(ctx, name, app, output):
    """Get alert details.

    Example:
        splunk-as alert get "My Alert" --app search
    """
    client = get_splunk_client()
    response = client.get(
        f"/servicesNS/-/{app}/saved/searches/{name}", operation="get alert"
    )

    if "entry" in response and response["entry"]:
        entry = response["entry"][0]
        content = entry.get("content", {})
        if output == "json":
            click.echo(format_json(entry))
        else:
            click.echo(f"Name: {entry.get('name')}")
            click.echo(f"Search: {content.get('search', '')[:80]}...")
            click.echo(f"Cron: {content.get('cron_schedule', 'Not scheduled')}")
            click.echo(f"Disabled: {content.get('disabled', False)}")
            click.echo(f"Alert Type: {content.get('alert_type', '')}")
            click.echo(f"Threshold: {content.get('alert_threshold', '')}")


@alert.command()
@click.option("--app", "-a", help="Filter by app.")
@click.option("--count", "-c", type=int, default=50, help="Maximum alerts to show.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format.",
)
@click.pass_context
@handle_cli_errors
def triggered(ctx, app, count, output):
    """List triggered alerts.

    Example:
        splunk-as alert triggered --app search --count 20
    """
    client = get_splunk_client()
    endpoint = build_endpoint("/alerts/fired_alerts", app=app)
    response = client.get(
        endpoint, params={"count": count}, operation="list triggered alerts"
    )

    alerts = [
        {
            "name": entry.get("name"),
            "trigger_time": entry.get("content", {}).get("trigger_time", ""),
            "severity": entry.get("content", {}).get("severity", ""),
            "triggered_alerts": entry.get("content", {}).get("triggered_alerts", 0),
        }
        for entry in response.get("entry", [])
    ]
    output_results(alerts, output, success_msg=f"Found {len(alerts)} triggered alerts")


@alert.command()
@click.argument("name")
@click.option("--app", "-a", default="search", help="App context.")
@click.pass_context
@handle_cli_errors
def acknowledge(ctx, name, app):
    """Acknowledge a triggered alert.

    Example:
        splunk-as alert acknowledge "My Alert" --app search
    """
    client = get_splunk_client()

    # Get alert group and acknowledge
    response = client.get(
        f"/servicesNS/-/{app}/alerts/fired_alerts/{name}",
        operation="get fired alert",
    )

    if "entry" in response and response["entry"]:
        # Delete the fired alert entry to acknowledge
        client.delete(
            f"/servicesNS/-/{app}/alerts/fired_alerts/{name}",
            operation="acknowledge alert",
        )
        print_success(f"Acknowledged alert: {name}")
    else:
        click.echo(f"No triggered alert found: {name}")


@alert.command()
@click.option("--name", "-n", required=True, help="Alert name.")
@click.option("--search", "-s", required=True, help="SPL query.")
@click.option("--app", "-a", default="search", help="App context.")
@click.option("--cron", required=True, help="Cron schedule (e.g., '*/5 * * * *').")
@click.option(
    "--condition",
    type=click.Choice(["always", "number_of_events", "number_of_results"]),
    default="number_of_events",
    help="Alert condition.",
)
@click.option("--threshold", type=int, default=1, help="Alert threshold.")
@click.pass_context
@handle_cli_errors
def create(ctx, name, search, app, cron, condition, threshold):
    """Create a new alert.

    Example:
        splunk-as alert create --name "Error Alert" --search "index=main error" --cron "*/5 * * * *"
    """
    client = get_splunk_client()

    data = {
        "name": name,
        "search": search,
        "cron_schedule": cron,
        "is_scheduled": True,
        "alert.track": True,
        "alert_type": condition,
        "alert_threshold": threshold,
    }

    client.post(
        f"/servicesNS/nobody/{app}/saved/searches",
        data=data,
        operation="create alert",
    )
    print_success(f"Created alert: {name}")
