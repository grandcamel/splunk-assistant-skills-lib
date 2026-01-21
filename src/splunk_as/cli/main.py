"""Splunk Assistant Skills CLI - Main entry point."""

import click

from splunk_as import __version__


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="splunk-as")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output.")
@click.pass_context
def cli(ctx: click.Context, output: str, verbose: bool, quiet: bool) -> None:
    """Splunk Assistant Skills CLI.

    A command-line interface for interacting with Splunk through
    various skill-based commands.

    Configure via environment variables:
        SPLUNK_SITE_URL, SPLUNK_TOKEN, SPLUNK_USERNAME, SPLUNK_PASSWORD

    Examples:

        splunk-as search oneshot "index=main | head 10"

        splunk-as job status abc123

        splunk-as metadata indexes
    """
    ctx.ensure_object(dict)
    ctx.obj["output"] = output
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def register_commands() -> None:
    """Register all command groups with the CLI."""
    from .commands.admin_cmds import admin
    from .commands.alert_cmds import alert
    from .commands.app_cmds import app
    from .commands.export_cmds import export
    from .commands.job_cmds import job
    from .commands.kvstore_cmds import kvstore
    from .commands.lookup_cmds import lookup
    from .commands.metadata_cmds import metadata
    from .commands.metrics_cmds import metrics
    from .commands.savedsearch_cmds import savedsearch
    from .commands.search_cmds import search
    from .commands.security_cmds import security
    from .commands.tag_cmds import tag

    cli.add_command(search)
    cli.add_command(job)
    cli.add_command(export)
    cli.add_command(metadata)
    cli.add_command(lookup)
    cli.add_command(kvstore)
    cli.add_command(savedsearch)
    cli.add_command(alert)
    cli.add_command(app)
    cli.add_command(security)
    cli.add_command(admin)
    cli.add_command(tag)
    cli.add_command(metrics)


# Register commands when module is loaded
register_commands()


if __name__ == "__main__":
    cli()
