import json

import cloup
import click

from promethium.utils import write_config_value, read_config, get_api_key, get_base_url
from promethium.cli.constants import BASE_URL


@cloup.group(
    short_help="Configure the Promethium CLI.",
    show_subcommand_aliases=True,
    aliases=["cfg"],
)
def config():
    ...


@config.command(short_help="Read config values", aliases=["r"])
def read():
    """
    Read config values and print to stdout.
    """
    config = read_config()
    if not config:
        click.echo("No config found.")
    click.echo(json.dumps(config, indent=2))


@config.command(short_help="Set your API key", aliases=["key"])
def credentials():
    """
    Set your API key.
    """
    current_key = get_api_key()
    prompt = "Enter your API key"
    if current_key:
        try:
            prompt += f" [{current_key[:4]}...{current_key[-4:]}]"
        except:  # NOSONAR
            pass
    api_key = click.prompt(prompt, type=str, default=current_key, show_default=False)
    write_config_value("Credentials", "api_key", api_key)


@config.command(short_help="Set the Promethium Base URL", aliases=["url"])
def base_url():
    """
    Set the Promethium Base URL. Use at your own risk.
    """
    if click.confirm("Set Base URL? Changing this setting is not recommended."):
        current_base_url = get_base_url()
        base_url = click.prompt(
            "Enter the Base URL", type=str, default=current_base_url
        )
        write_config_value("Connection", "base_url", base_url)
