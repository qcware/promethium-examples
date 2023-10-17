import sys
import pkg_resources

import cloup
import click

from promethium.cli.config import config
from promethium.cli.files import files
from promethium.cli.workflows import workflows
from promethium.cli.utils import get_api_key, get_base_url, ensure_config
from promethium.client import PromethiumClient

VERSION = pkg_resources.get_distribution("promethium").version


def _print_version(ctx, _, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(VERSION)
    ctx.exit()


@cloup.group(
    help="Command Line Interface (CLI) for Promethium by QC Ware",
    show_subcommand_aliases=True,
)
@cloup.option(
    "--version",
    "-v",
    is_flag=True,
    help="Print version and exit.",
    callback=_print_version,
    expose_value=False,
    is_eager=True,
)
@cloup.option("--api-key", "-k", help="Set Promethium API Key.")
@cloup.option("--base-url", "-b", help="Set Promethium Base URL.", hidden=True)
@cloup.option(
    "--show-tracebacks",
    "-t",
    help="Show error tracebacks",
    hidden=True,
    default=False,
    is_flag=True,
)
@cloup.pass_context
def run(ctx: cloup.Context, api_key: str, base_url: str, show_tracebacks: bool):
    if not show_tracebacks:
        sys.tracebacklimit = 0
    ensure_config()
    ctx.ensure_object(dict)
    cmd = ctx.invoked_subcommand
    if cmd in ["workflows", "files"]:
        api_key = get_api_key(ctx, api_key)
        base_url = get_base_url(ctx, base_url)
        ctx.obj["client"] = PromethiumClient(base_url=base_url, api_key=api_key)


for group in [config, workflows, files]:
    run.add_command(group)
