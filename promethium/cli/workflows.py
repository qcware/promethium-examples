import json
import uuid
import pathlib
from datetime import datetime

import cloup
from cloup.constraints import If, require_all
import click
import pytimeparse

from promethium.cli.utils import get_client_from_context
from promethium.models import (
    WorkflowKind,
    WorkflowStatus,
    ListWorkflowParams,
    CreateWorkflowParams,
)


wait_opts = cloup.option_group(
    "Wait options",
    "Options to control waiting for results",
    cloup.option("--wait", "-w", is_flag=True, help="Wait for Workflow to finish."),
    cloup.option(
        "--timeout",
        "-t",
        type=cloup.STRING,
        default="24h",
        show_default=True,
        help="Time to wait, in human readable terms, e.g. `13h 23m 42s`.",
    ),
    cloup.option(
        "--interval",
        "-i",
        type=cloup.INT,
        default=10,
        show_default=True,
        help="Polling interval in seconds.",
    ),
    cloup.option(
        "--output-dir",
        "-o",
        type=cloup.dir_path(exists=True),
        required=False,
        help="Output directory for results.",
    ),
)


@cloup.group(
    short_help="Manage Promethium workflows.",
    show_subcommand_aliases=True,
    aliases=["wf"],
)
@cloup.pass_context
def workflows(ctx: cloup.Context):  # NOSONAR
    ...


@workflows.command(short_help="Get information about a Workflow.", aliases=["r"])
@cloup.argument("workflow_id", type=cloup.UUID)
@cloup.pass_context
def read(ctx: cloup.Context, workflow_id: uuid.UUID):
    """
    Get metadata for the Workflow specified by WORKFLOW_ID.
    """
    click.echo(
        get_client_from_context(ctx)
        .workflows.get(workflow_id)
        .model_dump_json(indent=2)
    )


@workflows.command(short_help="Get the current status of a Workflow.", aliases=["s"])
@cloup.argument("workflow_id", type=cloup.UUID)
@cloup.pass_context
def status(ctx: cloup.Context, workflow_id: uuid.UUID):
    """
    Get the current status of the Workflow specified by WORKFLOW_ID.
    """
    click.echo(
        json.dumps(
            dict(
                status=get_client_from_context(ctx).workflows.status(workflow_id).value
            ),
            indent=2,
        )
    )


@workflows.command(short_help="List Workflows.", aliases=["ls"])
@cloup.option(
    "--kind",
    "-k",
    required=True,
    type=cloup.Choice([k.value for k in WorkflowKind], case_sensitive=False),
    help="Workflow kind (not case sensitive).",
)
@cloup.option(
    "--search",
    "-s",
    type=cloup.STRING,
    help="Search for workflow names containing this substring.",
)
@cloup.option(
    "--status",
    "-t",
    multiple=True,
    type=cloup.Choice([k.value for k in WorkflowStatus], case_sensitive=False),
    help="List of Workflow Statuses (not case sensitive).",
)
# @cloup.option(
#     "--started-before",
#     "-b",
#     type=cloup.DateTime(),
#     help="Workflows started before <datetime>.",
# )
# @cloup.option(
#     "--started-after",
#     "-a",
#     type=cloup.DateTime(),
#     help="Workflows started after <datetime>.",
# )
# @cloup.option(
#     "--stopped-before",
#     type=cloup.DateTime(),
#     help="Workflows started before <datetime>.",
# )
# @cloup.option(
#     "--stopped-after", type=cloup.DateTime(), help="Workflows started after <datetime>."
# )
@cloup.option(
    "--page",
    "-p",
    default=1,
    show_default=True,
    required=True,
    type=cloup.INT,
    help="Get page of results.",
)
@cloup.option(
    "--size",
    "-z",
    default=10,
    show_default=True,
    required=True,
    type=cloup.INT,
    help="Page size.",
)
@cloup.pass_context
def list(
    ctx: cloup.Context,
    kind: str,
    search: str,
    status: str,
    # started_before: datetime,
    # started_after: datetime,
    # stopped_before: datetime,
    # stopped_after: datetime,
    page: int,
    size: int,
):
    """
    List Workflows matching the filter criteria. Returns paged results.
    """
    params = ListWorkflowParams(
        kind=kind, search=search, status=status, page=page, size=size
    )
    workflows = get_client_from_context(ctx).workflows.list(params)
    click.echo(workflows.model_dump_json(indent=2))


@workflows.command(
    short_help="Submit a new Workflow.", aliases=["n"], show_constraints=True
)
@cloup.argument("input_file_path", type=cloup.file_path(allow_dash=True))
@wait_opts
@cloup.constraint(If("output_dir", then=require_all), ["wait"])
@cloup.constraint(If("wait", then=require_all), ["timeout", "interval"])
@cloup.pass_context
def new(
    ctx: cloup.Context,
    input_file_path: pathlib.Path,
    wait: bool,
    timeout: int,
    interval: int,
    output_dir: pathlib.Path,
):
    """
    Create a new Workflow with the JSON-formatted workflow definition file
    located at INPUT_FILE_PATH.

    If `--wait` is set and `--output-dir` is not, then the output will be the
    numeric results of the Workflow. Otherwise,a .zipped file containing the
    Workflow's complete results will be downloaded to the directory specified.
    """
    workflow_definition = CreateWorkflowParams(
        request=json.loads(input_file_path.read_text())
    ).request
    client = get_client_from_context(ctx)
    workflow = client.workflows.submit(workflow_definition)
    if not wait:
        click.echo(workflow.model_dump_json(indent=2))
    else:
        timeout_secs = pytimeparse.parse(timeout)
        client.workflows.wait(workflow.id, interval=interval, timeout=timeout_secs)
        if output_dir:
            output_dir.joinpath(f"{workflow.id}-results.zip").write_bytes(
                client.workflows.download(workflow.id)
            )
        else:
            click.echo(client.workflows.results(workflow.id).model_dump_json(indent=2))


@workflows.command(
    short_help="Get all Workflow results.", aliases=["dl"], show_constraints=True
)
@cloup.argument("workflow_id", type=cloup.UUID)
@wait_opts
@cloup.constraint(require_all, ["output_dir"])
@cloup.pass_context
def download(
    ctx: cloup.Context,
    workflow_id: uuid.UUID,
    wait: bool,
    timeout: int,
    interval: int,
    output_dir: pathlib.Path,
):
    """
    Download results of the Workflow specified by WORKFLOW_ID to `--output-dir`.

    If `--wait` is set, then the command will wait until `--timeout`, checking
    every `--interval` seconds.
    """
    client = get_client_from_context(ctx)
    if wait:
        timeout_secs = pytimeparse.parse(timeout)
        client.workflows.wait(workflow_id, interval=interval, timeout=timeout_secs)

    output_dir.joinpath(f"{workflow_id}-results.zip").write_bytes(
        client.workflows.download(workflow_id)
    )


@workflows.command(
    short_help="Get numeric Workflow results.", aliases=["res"], show_constraints=True
)
@cloup.argument("workflow_id", type=cloup.UUID)
@wait_opts
@cloup.pass_context
def results(
    ctx: cloup.Context,
    workflow_id: uuid.UUID,
    wait: bool,
    timeout: int,
    interval: int,
    output_dir: pathlib.Path,
):
    """
    Get numeric results of the Workflow specified by WORKFLOW_ID.

    If `--wait` is set, then the command will wait until `--timeout`, checking
    every `--interval` seconds.

    If `--output-dir` is specified, then the results will be saved to a
    JSON formatted file at that location.
    """
    client = get_client_from_context(ctx)
    if wait:
        timeout_secs = pytimeparse.parse(timeout)
        client.workflows.wait(workflow_id, interval=interval, timeout=timeout_secs)

    results = client.workflows.results(workflow_id)
    output = results.model_dump_json(indent=2)
    if output_dir:
        output_dir.joinpath(f"{workflow_id}-numeric-results.json").write_text(output)
    else:
        click.echo(output)


@workflows.command(short_help="Stop an in-progress Workflow.", aliases=["st"])
@cloup.argument("workflow_id", type=cloup.UUID)
@cloup.pass_context
def stop(ctx: cloup.Context, workflow_id: uuid.UUID):
    """
    Stop the Workflow specified by WORKFLOW_ID.
    """
    get_client_from_context(ctx).workflows.stop(workflow_id)
    click.echo(json.dumps(dict(workflow_id=workflow_id), indent=2))


@workflows.command(short_help="Delete a Workflow.", aliases=["rm"])
@cloup.argument("workflow_id", type=cloup.UUID)
@cloup.pass_context
def delete(ctx: cloup.Context, workflow_id: uuid.UUID):
    """
    Delete the Workflow specified by WORKFLOW_ID and its associated data.
    """
    get_client_from_context(ctx).workflows.delete(workflow_id)
    click.echo(json.dumps(dict(workflow_id=workflow_id), indent=2))
