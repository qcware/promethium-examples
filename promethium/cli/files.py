import json
import uuid
import typing
import pathlib

import click

from promethium.cli.utils import get_client_from_context
from promethium.models import (
    CreateSimpleFileRequest,
    CreateDirectoryRequest,
    UpdateFileRequest,
)
from promethium.utils import base64encode


@click.group(help="Manage your files.")
@click.pass_context
def files(ctx: click.Context):  # NOSONAR
    ...


@files.command(short_help="Get metadata for a file or directory.")
@click.argument("file_id", type=click.UUID)
@click.pass_context
def data(ctx: click.Context, file_id: uuid.UUID):
    """
    Get metadata for the file or directory specified by FILE_ID.
    """
    metadata = get_client_from_context(ctx).files.metadata(file_id)
    click.echo(json.dumps(metadata.model_dump(mode="json"), indent=2))


@files.command(short_help="Download file data.")
@click.argument("file_id", type=click.UUID)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(
        path_type=pathlib.Path, exists=True, file_okay=False, dir_okay=True
    ),
)
@click.pass_context
def get(
    ctx: click.Context, file_id: uuid.UUID, output_dir: typing.Optional[pathlib.Path]
):
    """
    Get file contents from FILE_ID. If --output-dir is not specified,
    print the contents of the file to stdout.
    """
    data = get_client_from_context(ctx).files.download(file_id)
    if output_dir:
        metadata = get_client_from_context(ctx).files.metadata(file_id)
        output_dir.joinpath(metadata.name).write_bytes(data)
    else:
        click.echo(data)


@files.command(short_help="List the contents of a directory.")
@click.argument("dir_id", type=click.UUID, required=False)
@click.option("--search", "-s", type=click.STRING)
@click.pass_context
def ls(ctx: click.Context, dir_id: uuid.UUID, search: typing.Optional[str]):
    """
    List the contents of the directory specified by DIR_ID. If DIR_ID
    is not provided, then all files will be listed.
    """
    page_gen = get_client_from_context(ctx).files.list(parent_id=dir_id, search=search)
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
    update = get_client_from_context(ctx).files.update(
        src_id, UpdateFileRequest(parent_id=dir_id)
    )
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
    directory = get_client_from_context(ctx).files.create(
        CreateDirectoryRequest(name=name, parent_id=dir_id, is_directory=True)
    )
    click.echo(json.dumps(directory.model_dump(mode="json"), indent=2))


@files.command(short_help="Upload file(s) from the local filesystem.")
@click.argument(
    "src",
    type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=pathlib.Path),
)
@click.argument("dir_id", type=click.UUID, required=False)
@click.pass_context
def cp(ctx: click.Context, src: pathlib.Path, dir_id: uuid.UUID):
    """
    Copy local file or directory contents at SRC to the directory with
    DIR_ID. If DIR_ID is not provided, then the files will be created
    in the user's root directory. Note: files with unsupported extensions
    will not be uploaded.
    """
    client = get_client_from_context(ctx)
    if src.is_file():
        file = client.files.create(
            CreateSimpleFileRequest(
                name=src.name,
                parent_id=dir_id,
                base64body=base64encode(src.read_bytes()),
                is_directory=False,
            )
        )
        output = file.model_dump(mode="json")
    elif src.is_dir():
        files = [
            CreateSimpleFileRequest(
                name=file.name,
                parent_id=dir_id,
                base64body=base64encode(file.read_bytes()),
                is_directory=False,
            )
            for file in src.iterdir()
            if file.is_file()
        ]
        batch = client.files.create_batch(files)
        output = [item.model_dump(mode="json") for item in batch]
    click.echo(json.dumps(output, indent=2))


@files.command(short_help="Delete a file or directory.")
@click.argument(
    "resource_id",
    type=click.UUID,
)
@click.pass_context
def rm(ctx: click.Context, resource_id: uuid.UUID):
    """
    Delete the file or directory specified by RESOURCE_ID
    """
    get_client_from_context(ctx).files.delete(resource_id)
    click.echo(json.dumps(dict(resource_id=str(resource_id))))
