import time
from uuid import UUID

from pydantic import UUID4

from promethium_sdk.models import (
    Workflow,
    WorkflowKind,
    WorkflowResult,
    WorkflowStatus,
    CreateGeometryOptimizationWorkflowRequest,
)
from promethium_sdk.client import PromethiumClient


prom = PromethiumClient()

# List files:
file_list = []
for page in prom.files.list(size=50):
    file_list.extend(page)

# Example file UUID:
file_id = UUID("4cc9d63a-8888-4c9b-b7ec-f507ded24c9d")

# File metadata:
meta = prom.files.metadata(file_id)

benzaldehyde = prom.files.download(file_id)

# Iterated list:
ts_list = []
for page in prom.workflows.list(kind=WorkflowKind.TorsionScan, size=50):
    ts_list.extend(page)

# List a selection of geometry optimization workflows:
go_list = prom.workflows.list(kind=WorkflowKind.GeometryOptimization, page=1, size=20)

# Pick a workflow:
workflow_id = UUID("27c5a58a-5689-4ab3-a2f7-9d4a4a49134f")

# Grab details of one workflow:
workflow: Workflow = prom.workflows.get(id=workflow_id)

# Grab the numeric results of one workflow:
workflow_result: WorkflowResult = prom.workflows.results(id=workflow_id)

# Download results of one workflow (as a zip file) to the current directory:
prom.workflows.download(id=workflow_id)

# Submit a workflow:
config = {
    "name": "client-example-geometry-optimization",
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {
            "id": str(file_id),
        },
        "system": {
            "params": {
                "basisname": "def2-tzvp",
                "jkfit_basisname": "def2-universal-jkfit",
                "xc_functional_name": "b3lyp",
                "xc_grid_scheme": "SG2",
            }
        },
        "hf": {
            "params": {
                "multiplicity": 1,
                "charge": 0,
                "g_convergence": 1.0e-8,
                "print_level": 2,
            }
        },
        "pes": {"params": {"coordinate_system_name": "redundant"}},
        "optimization": {
            "params": {"maxiter": 20},
            "outputs": {"gradient": False, "vibrational_frequencies": True},
        },
    },
    "resources": {"gpu_type": "a100"},
}
payload = CreateGeometryOptimizationWorkflowRequest(**config)
go_workflow = prom.workflows.submit(payload)
print("Workflow submitted, waiting for completion...")

# Wait for a workflow to finish:
prom.workflows.wait(id=go_workflow.id)

# Get the status of the workflow:
status = prom.workflows.status(id=go_workflow.id)
if status == WorkflowStatus.COMPLETED:
    print("Workflow completed successfully")
elif status == WorkflowStatus.FAILED:
    print("Workflow failed")
else:
    print(f"Workflow state: {status}")


# Grab the numeric results of the workflow:
go_result = prom.workflows.results(id=go_workflow.id)
molecule_str = go_result.get_artifact("optimized-molecule")
print(f"Optimized molecule:\n{molecule_str}")

# Submit a workflow and then cancel it:
workflow = prom.workflows.submit(payload)

# Wait a few seconds and cancel the workflow:
time.sleep(5)
prom.workflows.stop(id=workflow.id)

# Delete the earlier workflow:
prom.workflows.delete(id=go_workflow.id)
