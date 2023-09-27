from typing import Any, Dict, List, Optional

from pydantic import UUID4, BaseModel, Field

from promethium.models.models import Version, WorkflowKind, WorkflowStatus
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
