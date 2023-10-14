import json
import uuid
import typing

import click

from promethium.cli.utils import get_client_from_context, validate_uuid_or_path


@click.group(help="Manage your files.")
@click.pass_context
def files(ctx: click.Context):  # NOSONAR
    ...


@files.command(short_help="Get metadata for a file or directory.")
@click.argument("file_id", type=click.UUID)
@click.pass_context
def file(ctx: click.Context, file_id: uuid.UUID):
    """
    Get metadata for the file or directory specified by FILE_ID.
    """
    metadata = get_client_from_context(ctx).files.metadata(file_id)
    click.echo(json.dumps(metadata.model_dump(mode="json"), indent=2))


@files.command(short_help="List the contents of a directory.")
@click.argument("dir_id", type=click.UUID, required=False)
@click.option("--search", "-s", type=click.STRING)
@click.pass_context
def ls(ctx: click.Context, dir_id: uuid.UUID, search: typing.Optional[str]):
    """
    List the contents of the directory specified by DIR_ID. If DIR_ID
    is not provided, then all files will be listed.
    """
    page_gen = get_client_from_context(ctx).files.ls(parent_id=dir_id, search=search)
    contents = []
    for page in page_gen:
        contents.extend(page)
    click.echo(
        json.dumps([item.model_dump(mode="json") for item in contents], indent=2)
    )


@files.command(short_help="Move a file to a directory.")
@click.argument("src_id", type=click.UUID)
@click.argument("dir_id", type=click.UUID, required=False)
@click.pass_context
def mv(ctx: click.Context, src_id: uuid.UUID, dir_id: uuid.UUID):
    """
    Move the file or directory specified by SRC_ID to the directory
    specified by DIR_ID. If DIR_ID is not provided, then the file will
    be moved to the root directory.
    """
    update = get_client_from_context(ctx).files.mv(src_id, dir_id)
    click.echo(json.dumps(update.model_dump(mode="json"), indent=2))


@files.command(short_help="Create a new directory.")
@click.argument("name", type=click.STRING)
@click.argument("dir_id", type=click.UUID, required=False)
@click.pass_context
def mkdir(ctx: click.Context, name: str, dir_id: uuid.UUID):
    """
    Create a new directory with NAME and DIR_ID. If DIR_ID
    is not provided, then the new directory will be created in the
    user's root directory.
    """
    directory = get_client_from_context(ctx).files.mkdir(name, dir_id)
    click.echo(json.dumps(directory.model_dump(mode="json"), indent=2))


@files.command(
    short_help="Remote copy files between Promethium and the local filesystem.",
    context_settings={"ignore_unknown_options": True},
)
@click.argument(
    "src",
)
@click.argument(
    "dest",
)
@click.pass_context
def rcp(
    ctx: click.Context,
    src: str,
    dest: str,
):
    """
    Remote copy files between Promethium and the local filesystem.

    If SRC is a Promethium File ID, the file will be downloaded to
    the directory at DEST. If SRC is a directory, the zipped contents
    of the directory will be downloaded to DEST.

    If SRC is a local file, the file will be uploaded to the Promethium
    directory ID specified at DEST. If SRC is a local directory, then
    its contents will be uploaded to DEST. Only files with supported
    extensions will be uploaded.
    """
    res = get_client_from_context(ctx).files.rcp(
        validate_uuid_or_path(src), validate_uuid_or_path(dest)
    )
    if res:
        click.echo(json.dumps([item.model_dump(mode="json") for item in res], indent=2))


@files.command(short_help="Delete a file or directory.")
@click.argument(
    "resource_id",
    type=click.UUID,
)
@click.pass_context
def rm(ctx: click.Context, resource_id: uuid.UUID):
    """
    Delete the file or directory specified by RESOURCE_ID.
    """
    get_client_from_context(ctx).files.rm(resource_id)
    click.echo(str(resource_id))
