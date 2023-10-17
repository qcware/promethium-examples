import os
import pathlib
from uuid import UUID
from functools import partial
from typing import Iterator, Optional, Type, Union, List

from httpx import Client, HTTPStatusError
from pydantic import UUID4

from promethium.exceptions import FileNotFound, WorkflowNotFound
from promethium.models import (
    Workflow,
    FileMetadata,
    PageWorkflow,
    WorkflowResult,
    WorkflowStatus,
    PageFileMetadata,
    UpdateFileRequest,
    ListWorkflowParams,
    ListFileMetadataParams,
    CreateDirectoryRequest,
    CreateSimpleFileRequest,
    CreateTorsionScanWorkflowRequest,
    CreateConformerSearchWorkflowRequest,
    CreateGeometryOptimizationWorkflowRequest,
    CreateSinglePointCalculationWorkflowRequest,
    CreateReactionPathOptimizationWorkflowRequest,
    CreateTransitionStateOptimizationWorkflowRequest,
    CreateInteractionEnergyCalculationWorkflowRequest,
    CreateTransitionStateOptimizationFromEndpointsWorkflowRequest,
)
from promethium.utils import (
    wait_for_workflows_to_complete,
    filter_unsupported_extensions,
    base64encode,
    TERMINAL_STATUSES,
    NON_TERMINAL_STATUSES,
)
from promethium.filesys_utils import is_path_exists_or_creatable_portable


def handle_response(response, not_found_exception: Type):
    try:
        response.raise_for_status()
    except HTTPStatusError as e:
        if e.response.status_code == 404:
            raise not_found_exception(id)
        else:
            raise e
    return response


class BaseResource:
    def __init__(self, client: Client) -> None:
        self._client = client

    @property
    def client(self) -> Client:
        return self._client


class Files(BaseResource):
    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self._handle_response = partial(
            handle_response, not_found_exception=FileNotFound
        )

    @classmethod
    def metadata_from_items(cls, items: list[dict]) -> list[FileMetadata]:
        return [FileMetadata(**file) for file in items]

    # API

    def metadata(self, id: UUID4) -> FileMetadata:
        response = self._client.get(f"/v0/files/{id}")
        self._handle_response(response)
        return FileMetadata(**response.json())

    def download(self, id: UUID4) -> Union[str, bytes]:
        response = self._client.get(f"/v0/files/{id}/download", follow_redirects=True)
        self._handle_response(response)
        return response.content

    def list(
        self,
        params: ListFileMetadataParams,
    ) -> Union[Iterator[List[FileMetadata]], List[FileMetadata]]:
        resp = self._client.get(
            "/v0/files",
            params=params.model_dump(
                mode="json", exclude_none=True, exclude_unset=True
            ),
        )
        self._handle_response(resp)
        return PageFileMetadata(**resp.json())

    def update(self, id: UUID4, update: UpdateFileRequest) -> FileMetadata:
        response = self._client.patch(
            f"/v0/files/{id}",
            data=update.model_dump_json(exclude_none=True, exclude_unset=True),
        )
        self._handle_response(response)
        return FileMetadata(**response.json())

    def create(
        self, create: Union[CreateSimpleFileRequest, CreateDirectoryRequest]
    ) -> FileMetadata:
        response = self._client.post(
            "/v0/files",
            data=create.model_dump_json(exclude_none=True, exclude_unset=True),
        )
        self._handle_response(response)
        return FileMetadata(**response.json())

    def create_batch(
        self, batch: List[Union[CreateSimpleFileRequest, CreateDirectoryRequest]]
    ) -> List[FileMetadata]:
        response = self._client.post(
            "/v0/files/batch",
            json=[
                item.model_dump(mode="json", exclude_none=True, exclude_unset=True)
                for item in batch
            ],
        )
        self._handle_response(response)
        return [FileMetadata(**item) for item in response.json()]

    def delete(self, id: UUID4) -> None:
        response = self._client.delete(f"/v0/files/{id}")
        self._handle_response(response)

    # FILESYSTEM OPS

    def file(self, id: UUID4) -> FileMetadata:
        return self.metadata(id)

    def ls(
        self,
        parent_id: Optional[UUID4] = None,
        search: Optional[str] = None,
    ) -> Union[Iterator, List[FileMetadata]]:
        page_gen = self.list(parent_id=parent_id, search=search)
        contents = []
        for page in page_gen:
            contents.extend(page)
        return contents

    def mkdir(self, name, parent_id: Optional[UUID4] = None) -> FileMetadata:
        return self.create(
            CreateDirectoryRequest(name=name, parent_id=parent_id, is_directory=True)
        )

    def mv(self, id, new_parent_id: Optional[UUID4] = None) -> FileMetadata:
        return self.update(id, UpdateFileRequest(parent_id=new_parent_id))

    def rcp(  # NOSONAR
        self, src: Union[UUID4, pathlib.Path], dest: Union[UUID4, pathlib.Path]
    ) -> Optional[FileMetadata]:
        if isinstance(src, UUID) and isinstance(dest, pathlib.Path):
            if not dest.is_dir:
                raise ValueError("Destination path is not a directory")
            if not is_path_exists_or_creatable_portable(str(dest)):
                raise ValueError("Destination path does not exist or is not creatable")
            data = self.download(src)
            src_metadata = self.metadata(src)
            filename = src_metadata.name
            if src_metadata.is_directory:
                filename += ".zip"
            with open(dest.joinpath(filename), "wb") as outfile:
                outfile.write(data)
        elif isinstance(src, pathlib.Path) and isinstance(dest, UUID):
            dest_metadata = self.metadata(dest)
            if not dest_metadata.is_directory:
                raise ValueError("Destination is not a directory")
            if not is_path_exists_or_creatable_portable(str(src)):
                raise ValueError("Source path is not a file or directory")
            to_upload = filter_unsupported_extensions(
                [
                    CreateSimpleFileRequest(
                        name=file.name,
                        parent_id=dest,
                        is_directory=False,
                        base64body=base64encode(file.read_bytes()),
                    )
                    for file in src.iterdir()
                    if file.is_file()
                ]
                if src.is_dir()
                else [
                    CreateSimpleFileRequest(
                        name=src.name,
                        parent_id=dest,
                        is_directory=False,
                        base64body=base64encode(src.read_bytes()),
                    )
                ]
            )
            return self.create_batch(to_upload)
        else:
            raise ValueError(
                "One of src and dest must be a UUID and the other must be a filesystem path"
            )

    def rm(self, id: UUID4) -> None:
        return self.delete(id)


class Workflows(BaseResource):
    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self._handle_response = partial(
            handle_response, not_found_exception=WorkflowNotFound
        )

    @classmethod
    def from_items(cls, items: list[dict]) -> list[Workflow]:
        return [Workflow(**workflow) for workflow in items]

    # API

    def get(self, id: UUID4) -> Workflow:
        workflow_response = self._client.get(f"/v0/workflows/{id}")
        self._handle_response(workflow_response)
        return Workflow(**workflow_response.json())

    def status(self, id: UUID4) -> WorkflowStatus:
        return self.get(id).status

    def list(self, params: ListWorkflowParams) -> PageWorkflow:
        resp = self._client.get(
            "/v0/workflows",
            params=params.model_dump(
                mode="json", exclude_none=True, exclude_unset=True
            ),
        )
        self._handle_response(resp)
        return PageWorkflow(**resp.json())

    def submit(
        self,
        workflow_request: Union[
            CreateTorsionScanWorkflowRequest,
            CreateConformerSearchWorkflowRequest,
            CreateGeometryOptimizationWorkflowRequest,
            CreateSinglePointCalculationWorkflowRequest,
            CreateReactionPathOptimizationWorkflowRequest,
            CreateTransitionStateOptimizationWorkflowRequest,
            CreateInteractionEnergyCalculationWorkflowRequest,
            CreateTransitionStateOptimizationFromEndpointsWorkflowRequest,
        ],
    ) -> Workflow:
        payload = workflow_request.model_dump_json(
            exclude_unset=True, exclude_none=True
        )
        response = self._client.post("/v0/workflows", data=payload)
        response.raise_for_status()
        return Workflow(**response.json())

    def results(self, id: UUID4) -> WorkflowResult:
        response = self._client.get(f"/v0/workflows/{id}/results")
        self._handle_response(response)
        return WorkflowResult(**response.json())

    def wait(self, id: UUID4, interval: int = 10, timeout: int = 24 * 3600) -> None:
        wait_for_workflows_to_complete(
            client=self._client, workflow_ids=[id], interval=interval, timeout=timeout
        )

    def stop(self, id: UUID) -> None:
        response = self._client.post(f"/v0/workflows/{id}/stop")
        self._handle_response(response)

    def download(self, id: UUID4) -> Union[str, bytes]:
        response = self._client.get(
            f"/v0/workflows/{id}/results/download", follow_redirects=True
        )
        self._handle_response(response)
        return response.content

    def delete(self, id: UUID4) -> None:
        """Deletes a workflow, or raises if it doesn't exist,
        or otherwise can't be deleted e.g., if it is not in a terminal state.

        409 Conflict - if the workflow is not in a terminal state
        """
        response = self._client.delete(f"/v0/workflows/{id}")
        self._handle_response(response)


class PromethiumClient:
    def __init__(
        self, base_url: Optional[str] = None, api_key: Optional[str] = None
    ) -> None:
        self.base_url = (
            os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
            if base_url is None
            else base_url
        )
        self._client = Client(
            base_url=self.base_url,
            headers={
                "X-API-KEY": os.environ["PM_API_KEY"] if api_key is None else api_key
            },
        )
        self._workflows = Workflows(client=self.client)
        self._files = Files(client=self.client)

    @property
    def client(self) -> Client:
        return self._client

    @property
    def files(self) -> Files:
        return self._files

    @property
    def workflows(self) -> Workflows:
        return self._workflows
