from functools import partial
import os
from typing import Generator, Optional, Type, Union
from uuid import UUID

from httpx import Client, HTTPStatusError
from pydantic import UUID4

from promethium.exceptions import FileNotFound, WorkflowNotFound
from promethium.models import (
    FileMetadata,
    Workflow,
    WorkflowKind,
    WorkflowResult,
    WorkflowStatus,
)
from promethium.utils import (
    wait_for_workflows_to_complete,
    TERMINAL_STATUSES,
    NON_TERMINAL_STATUSES,
)


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

    def metadata(self, id: UUID4) -> Union[str, bytes]:
        response = self._client.get(f"/v0/files/{id}")
        self._handle_response(response)
        return response.json()

    def download(self, id: UUID4) -> Union[str, bytes]:
        response = self._client.get(f"/v0/files/{id}/download", follow_redirects=True)
        self._handle_response(response)
        return response.content

    def list(
        self, page: Optional[int] = None, size: int = 10
    ) -> Union[Generator, list[FileMetadata]]:
        iterate = page is None
        page = 1 if page is None else page
        total = page * size + 1
        while (page - 1) * size < total:
            response = self._client.get("/v0/files", params={"page": page})
            self._handle_response(response)
            page_json = response.json()
            if not iterate:
                return self.metadata_from_items(page_json["items"])
            yield self.metadata_from_items(page_json["items"])
            page += 1
            total = page_json["total"]


class Workflows(BaseResource):
    def __init__(self, client: Client) -> None:
        super().__init__(client)
        self._handle_response = partial(
            handle_response, not_found_exception=WorkflowNotFound
        )

    def get(self, id: UUID4) -> Workflow:
        workflow_response = self._client.get(f"/v0/workflows/{id}")
        self._handle_response(workflow_response)
        return Workflow(**workflow_response.json())

    @classmethod
    def from_items(cls, items: list[dict]) -> list[Workflow]:
        return [Workflow(**workflow) for workflow in items]

    def status(self, id: UUID4) -> WorkflowStatus:
        return self.get(id).status

    def list(
        self, kind: WorkflowKind, page: Optional[int] = None, size: int = 10
    ) -> Union[Generator, list[Workflow]]:
        iterate = page is None
        page = 1 if page is None else page
        total = page * size + 1
        while (page - 1) * size < total:
            response = self._client.get(
                "/v0/workflows", params={"kind": kind.value, "page": page}
            )
            self._handle_response(response)
            page_json = response.json()
            if not iterate:
                return self.from_items(page_json["items"])
            yield self.from_items(page_json["items"])
            page += 1
            total = page_json["total"]

    def submit(self, workflow_request) -> Workflow:
        payload = workflow_request.json(exclude_unset=True, exclude_none=True)
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

    def download(self, id: UUID4, path: Optional[str] = None) -> None:
        path = os.getcwd() if path is None else path
        response = self._client.get(
            f"/v0/workflows/{id}/results/download", follow_redirects=True
        )
        self._handle_response(response)

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
            os.getenv("PROMETHIUM_API_BASE_URL", "https://api.promethium.qcware.com")
            if base_url is None
            else base_url
        )
        self._client = Client(
            base_url=self.base_url,
            headers={
                "X-API-KEY": os.environ["PROMETHIUM_API_KEY"]
                if api_key is None
                else api_key
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
