import os

from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateGeometryOptimizationWorkflowRequest,
)
from promethium_sdk.utils import base64encode

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

mol = base64encode(
"""9

    O           -1.510407226976     0.757898746844     0.000000000000
    O           -0.553334234073    -1.306832947272     0.000000000000
    C            0.851836372408     0.670262334922     0.000000000000
    C           -0.435392872548    -0.091344744168     0.000000000000
    C            2.037631538003     0.030293859895     0.000000000000
    H            0.778714996763     1.768162197756     0.000000000000
    H            2.070317763114    -1.070327443612     0.000000000000
    H            2.990077611988     0.580280001156     0.000000000000
    H           -2.306286818048     0.180092981979     0.000000000000
"""
)

job_params = {
    "name": "api_hessian_timings",
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {"base64data": mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": "def2-svp",
                "jkfit_basisname": "def2-universal-jkfit",
                "methodname": "b3lyp",
                "xc_grid_scheme": "SG1",
            },
        },
        "hf": {
            "params": {
                "multiplicity": 1,
                "charge": 0,
                "g_convergence": 1.0e-6,
                "print_level": 2,
                "print_timings": True,
                "print_gradient_timings": True,
                # Note: this will fail if multiplicity != 1 when print_hessian_timings is True.
                # This will resolve itself when UKS hessians are available.
                "print_hessian_timings": True,
            },
        },
        "pes": {
            "params": {
                "coordinate_system_name": "redundant",
                # Toggle to force numerical hessian (default is analytical):
                # "force_numerical_hessian": True,
            },
        },
        "optimization": {
            "params": {
                "maxiter": 200,
                "g_convergence": 1.0e-3,
            },
            "outputs": {"gradient": True, "vibrational_frequencies": True},
        },
    },
    "resources": {"gpu_type": gpu_type},
}

prom = PromethiumClient()
payload = CreateGeometryOptimizationWorkflowRequest(**job_params)
workflow = prom.workflows.submit(payload)
print(f"Workflow submitted (id: {workflow.id})")

prom.workflows.wait(workflow.id)

workflow = prom.workflows.get(workflow.id)
print(f"Workflow {workflow.name} completed with status: {workflow.status}")
print(f"Workflow completed in {workflow.duration_seconds:.2f}s")

go_results = prom.workflows.results(workflow.id)
with open(os.path.join(foldername, f"{workflow.name}_results.json"), "w") as fp:
    fp.write(go_results.model_dump_json(indent=2))

# Numeric results:
energy = go_results.results["optimization"]["energy"]
print(energy)

# Download:
with open(os.path.join(foldername, f"{workflow.name}_results.zip"), "wb") as fp:
    fp.write(prom.workflows.download(workflow.id))
