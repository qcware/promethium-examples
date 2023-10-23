from typing import Any, Dict, List, Optional, Union

from pydantic import UUID4, BaseModel, Field

from promethium.models import (
    Version,
    WorkflowKind,
    WorkflowStatus,
    CreateTorsionScanWorkflowRequest,
    CreateConformerSearchWorkflowRequest,
    CreateGeometryOptimizationWorkflowRequest,
    CreateSinglePointCalculationWorkflowRequest,
    CreateReactionPathOptimizationWorkflowRequest,
    CreateTransitionStateOptimizationWorkflowRequest,
    CreateInteractionEnergyCalculationWorkflowRequest,
    CreateTransitionStateOptimizationFromEndpointsWorkflowRequest,
)
from promethium.utils import decode_artifact


class WorkflowResult(BaseModel):
    id: UUID4 = Field(..., description="The unique id of the workflow", title="Id")
    kind: WorkflowKind = Field(
        ...,
        description="The type of workflow; can be one of ['TorsionScan', 'ConformerSearch', 'SinglePointCalculation', 'GeometryOptimization', 'InteractionEnergyCalculation', 'ReactionPathOptimization', 'TransitionStateOptimization', 'TransitionStateOptimizationFromEndpoints']",
    )
    api_version: Optional[Version] = Field("v1", title="Version")
    status: WorkflowStatus = Field(
        ...,
        description="The status of the workflow; can be one of ['CANCELED', 'COMPLETED', 'FAILED', 'RUNNING', 'TERMINATED', 'TIMED_OUT']",
    )
    results: Dict[str, Any] = Field(None, title="Results")

    @property
    def artifacts(self) -> Dict[str, Any]:
        try:
            return self.results["artifacts"]
        except KeyError:
            return {}

    def get_artifact(self, name: str) -> Any:
        try:
            return decode_artifact(self.artifacts[name])
        except KeyError:
            raise ValueError(f"Artifact {name} not found")


class _PageBase(BaseModel):
    page: Optional[int] = Field(1, description="Page of results.")
    size: Optional[int] = Field(10, description="Size of results page.")


class ListFileMetadataParams(_PageBase):
    parent_id: Optional[UUID4] = Field(
        None, description="List files and directories in this directory."
    )
    search: Optional[str] = Field(
        None,
        description="Get files and directories where `name` matches this substring.",
    )


class ListWorkflowParams(_PageBase):
    kind: WorkflowKind = Field(
        ...,
        description="The kind of the workflow.",
    )
    search: Optional[str] = Field(
        None, description="Get workflows where `name` matches this substring."
    )
    status: Optional[List[WorkflowStatus]] = Field(
        [],
        description="The status of the workflow.",
    )


class CreateWorkflowParams(BaseModel):
    request: Union[
        CreateTorsionScanWorkflowRequest,
        CreateConformerSearchWorkflowRequest,
        CreateGeometryOptimizationWorkflowRequest,
        CreateSinglePointCalculationWorkflowRequest,
        CreateReactionPathOptimizationWorkflowRequest,
        CreateTransitionStateOptimizationWorkflowRequest,
        CreateInteractionEnergyCalculationWorkflowRequest,
        CreateTransitionStateOptimizationFromEndpointsWorkflowRequest,
    ]
