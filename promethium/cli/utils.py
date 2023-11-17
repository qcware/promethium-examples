import os
import uuid
import typing
import pathlib
import configparser

import cloup
import click

from promethium.cli.constants import BASE_URL, CONFIG_FILENAME
from promethium.client import PromethiumClient


def ensure_config(config_dir: pathlib.Path = pathlib.Path.home()) -> None:
    """Ensure config file exists at specified location.

    Args:
        config_dir (pathlib.Path, optional): Directory where conifig is saved. Defaults to pathlib.Path.home().
    """
    config = configparser.ConfigParser()
    if not config.read(config_dir.joinpath(CONFIG_FILENAME)):
        write_config_value("Connection", "base_url", BASE_URL)


def read_config(config_dir: pathlib.Path = pathlib.Path.home()) -> dict:
    """Read config .INI file and return config values as a dict.

    Args:
        config_dir (pathlib.Path, optional): Directory where conifig is saved. Defaults to pathlib.Path.home().

    Returns:
        dict: Config returned as key-value pairs, can contain nested dicts.
    """
    config = configparser.ConfigParser()
    config.read(config_dir.joinpath(CONFIG_FILENAME))
    return config._sections


def write_config_value(
    section: str,
    key: str,
    value: str,
    config_dir: pathlib.Path = pathlib.Path.home(),
) -> None:
    """Write config values to the file at the specified location.

    Args:
        section (str): _description_
        key (str): _description_
        value (str): _description_
        config_dir (pathlib.Path, optional): _description_. Defaults to pathlib.Path.home().
    """
    config = configparser.ConfigParser()
    configpath = config_dir.joinpath(CONFIG_FILENAME)
    config.read(configpath)
    config[section] = {}
    config[section][key] = value
    with open(config_dir.joinpath(CONFIG_FILENAME), "w") as configfile:
        config.write(configfile)


def _get_api_key_from_config(config: dict) -> typing.Optional[str]:
    if config:
        if creds := config.get("Credentials"):
            return creds.get("api_key")
    return None


def _get_base_url_from_config(config: dict) -> typing.Optional[str]:
    if config:
        if creds := config.get("Connection"):
            return creds.get("base_url")
    return None


def get_api_key(ctx: cloup.Context, value: typing.Any) -> str:
    api_key = (
        value or os.environ.get("PM_API_KEY") or _get_api_key_from_config(read_config())
    )
    if not api_key:
        click.echo(
            """
Promethium API key not found. API keys are set in the following order of precedence:
    1. Run this script with the `--api-key` or `-k` option.
    2. Set the `PM_API_KEY` environment variable.
    3. Run `promethium config credentials` and follow the prompt."""
        )
        ctx.exit(1)
    return api_key


def get_base_url(ctx: cloup.Context, value: typing.Any) -> str:
    base_url = (
        value
        or os.environ.get("PM_BASE_URL")
        or _get_base_url_from_config(read_config())
    )
    if not base_url:
        click.echo(
            """
Promethium Base URL not found. The Base URL is set in the following order of precedence:
    1. Run this script with the `--base-url` or `-b` option.
    2. Set the `PM_BASE_URL` environment variable.
    3. Run `promethium config base-url` and follow the prompt."""
        )
        ctx.exit(1)
    return base_url


def get_client_from_context(ctx: cloup.Context) -> PromethiumClient:
    return ctx.obj["client"]


def validate_uuid_or_path(value: str) -> typing.Union[uuid.UUID, pathlib.Path]:
    try:
        return uuid.UUID(value)
    except ValueError:
        pass
    return pathlib.Path(value)


page_options = cloup.option_group(
    "Paging options",
    "",
    cloup.option(
        "--page",
        "-p",
        default=1,
        show_default=True,
        required=True,
        type=cloup.INT,
        help="Get page of results.",
    ),
    cloup.option(
        "--size",
        "-z",
        default=10,
        show_default=True,
        required=True,
        type=cloup.INT,
        help="Page size.",
    ),
)
