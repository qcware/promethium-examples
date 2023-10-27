import base64
import os

from promethium.client import PromethiumClient
from promethium.models import (
    CreateGeometryOptimizationWorkflowRequest,
)

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

mol = base64.b64encode(
    b"""
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
).decode("utf-8")

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
                "xc_functional_name": "b3lyp",
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
                "convergence": "strict",
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

prom.workflows.wait(workflow.id)

workflow = prom.workflows.get(workflow.id)
print(f"Workflow {workflow.name} completed with status: {workflow.status}")
print(f"Workflow completed in {workflow.duration_seconds:.2f}s")

spc_results = prom.workflows.results(workflow.id)
with open(f"{foldername}/{workflow.name}_results.json", "w") as fp:
    fp.write(spc_results.model_dump_json(indent=2))

# Numeric results:
energy = spc_results.results["optimization"]["energy"]
print(energy)

# Download:
prom.workflows.download(workflow.id)
