import os

from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateReactionPathOptimizationWorkflowRequest,
)
from promethium_sdk.utils import (
    base64encode,
)

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")
dir_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
)

if not os.path.exists(foldername):
    os.makedirs(foldername)

n = 4
workflow_ids = []

prom = PromethiumClient()

for i in range(1, n + 1):
    with open(os.path.join(dir_path, f"{i}/reactant.xyz"), "r") as fp:
        reactant = base64encode(fp.read())
    with open(os.path.join(dir_path, f"{i}/product.xyz"), "r") as fp:
        product = base64encode(fp.read())

    job_params = {
        "name": f"API Reaction Path Optimization: {i}",
        "version": "v1",
        "kind": "ReactionPathOptimization",
        "parameters": {
            "reactant": {
                "base64data": reactant,
                "filetype": "xyz",
                "params": {
                    "geometry_optimize": True,
                },
            },
            "product": {
                "base64data": product,
                "filetype": "xyz",
                "params": {
                    "geometry_optimize": True,
                },
            },
            "system": {
                "params": {
                    "basisname": "def2-svp",
                    "jkfit_basisname": "def2-universal-jkfit",
                    "xc_functional_name": "b3lyp",
                    "xc_grid_scheme": "SG1",
                    "threshold_pq": 1.0e-12,
                },
            },
            "hf": {
                "params": {
                    "multiplicity": 1,
                    "charge": 0,
                    "g_convergence": 1.0e-6,
                    "print_level": 0,
                },
            },
            "pes": {
                "params": {"coordinate_system_name": "redundant"},
            },
            "optimization": {
                "params": {
                    "maxiter": 200,
                },
            },
            "interpolation": {
                "params": {
                    "rk_thresh": 1.0e-3,
                    "integrator": "rk45",
                    "dt": 0.01,
                    "nbeads": 11,
                },
            },
            "neb": {
                "params": {"force_constant_upper": 0.10, "force_constant_lower": 0.01},
            },
            "fire": {
                "params": {
                    "g_convergence": 5.0e-3,
                    "dt_start": 0.5,
                    "alpha_start": 0.25,
                },
            },
        },
        "resources": {"gpu_type": gpu_type},
    }

    payload = CreateReactionPathOptimizationWorkflowRequest(**job_params)
    workflow = prom.workflows.submit(payload)
    workflow_ids.append(workflow.id)

# Wait for all workflows to complete:
for workflow_id in workflow_ids:
    prom.workflows.wait(workflow_id)

# Get results:
for i, workflow_id in enumerate(workflow_ids):
    workflow = prom.workflows.get(workflow_id)
    print(f"Workflow {workflow.name} completed with status: {workflow.status}")
    print(f"Workflow completed in {workflow.duration_seconds:.2f}s")

    workflow_results = prom.workflows.results(workflow.id)
    with open(f"{foldername}/{i}_{workflow.name}_results.json", "w") as fp:
        fp.write(workflow_results.model_dump_json(indent=2))

    # Download:
    prom.workflows.download(workflow.id)
