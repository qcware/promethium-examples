import os
from typing import Callable, Generator
from uuid import uuid4

from httpx import Client, HTTPStatusError
import pandas as pd

from promethium.models import Workflow


class WorkflowNotFound(Exception):
    pass



class Workflows:

    def __init__(self, client: Client) -> None:
        self._client = client

    def get(self, id: str) -> Workflow:
        workflow_response = self._client.get(f"/v0/workflows/{id}")
        try:
            workflow_response.raise_for_status()
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                raise WorkflowNotFound(id)
            else:
                raise e        
        return Workflow(**workflow_response.json())

    def list(self, kind: str, size: int = 10):
        page = 1
        total = page * size + 1
        while (page - 1) * size < total:
            page_json = self._client.get("/v0/workflows", params={"kind": kind, "page": page}).json()
            yield page_json["items"]
            page += 1
            total = page_json["total"]
        
    def results(self, id: uuid4):
        response = self._client.get(f"/v0/workflows/{id}/results")
        try:
            response.raise_for_status()
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                raise WorkflowNotFound(id)
            else:
                raise e
        return response.json()

    def download(self, id: uuid4, path: str):
        raise NotImplementedError("TODO: Implement this")


class PromethiumClient:
    
    def __init__(self, api_key=None) -> None:
        self._client = Client(
            base_url=os.getenv("PROMETHIUM_API_BASE_URL", "https://api.promethium.qcware.com"),
            headers={
                "X-API-KEY": os.environ['PROMETHIUM_API_KEY'] if api_key is None else api_key
            }
        )
        self.workflows = Workflows(client=self.client)

    @property
    def client(self) -> Client:
        return self._client

    def workflows(self) -> Workflows:
        return self.workflows
    