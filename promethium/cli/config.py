import json

import click

from promethium.cli.utils import write_config_value, read_config


@click.group(short_help="Configure the Promethium CLI.")
def config():
    ...


@config.command(short_help="Read config values")
def read():
    config = read_config()
    if not config:
        click.echo("No config found.")
    click.echo(json.dumps(config, indent=2))


@config.command(short_help="Set your API key")
def credentials():
    """
    Set your API key.
    """
    api_key = click.prompt("Enter your API key", type=str)
    write_config_value("Credentials", "api_key", api_key)


@config.command(short_help="Set the Promethium Base URL")
def base_url():
    """
    Set the Promethium Base URL. Use at your own risk.
    """
    if click.confirm("Set Base URL? Changing this setting is not recommended."):
        base_url = click.prompt("Enter the base URL", type=str)
        write_config_value("Connection", "base_url", base_url)
