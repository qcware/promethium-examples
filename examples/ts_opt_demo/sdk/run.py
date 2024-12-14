import os

from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateTransitionStateOptimizationWorkflowRequest,
)
from promethium_sdk.utils import base64encode

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

mol = base64encode(
"""
  C -1.254249740 0.397846920 -0.466359900
  C -0.444130910 1.062523780 0.618694870
  H -0.172744960 2.104512570 0.468098900
  H -0.773918840 0.809917830 1.621565670
  C 0.972968800 -0.042175990 0.419309910
  O 1.642537660 0.368789920 -0.715645850
  O -1.469148700 -0.843142830 -0.274219940
  O 0.499835900 -1.188352760 0.488417900
  H 1.570739680 -0.352353930 -1.351279720
  H -1.006075790 0.765688840 -1.469513700
  H -2.081021580 1.057364780 -0.006261000
  H 1.429694710 0.407351920 1.319100730
"""
)

job_params = {
    "name": "api_ts_opt",
    "version": "v1",
    "kind": "TransitionStateOptimization",
    "parameters": {
        "molecule": {
            "base64data": mol,
            "filetype": "xyz",
        },
        "system": {
            "params": {
                "basisname": "def2-svp",
                "jkfit_basisname": "def2-universal-jkfit",
                "methodname": "b3lyp",
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
            "params": {
                "coordinate_system_name": "cartesian",
            }
        },
        "optimization": {
            "params": {
                "maxiter": 200,
                "strict_convergence": True,
                "eigenvector_convergence": 1e-5,
            },
            "outputs": {"vibrational_frequencies": True},
        },
    },
    "resources": {"gpu_type": gpu_type},
}

prom = PromethiumClient()
payload = CreateTransitionStateOptimizationWorkflowRequest(**job_params)
workflow = prom.workflows.submit(payload)
print(f"Workflow submitted (id: {workflow.id})")

prom.workflows.wait(workflow.id)

workflow = prom.workflows.get(workflow.id)
print(f"Workflow {workflow.name} completed with status: {workflow.status}")
print(f"Workflow completed in {workflow.duration_seconds:.2f}s")

tso_results = prom.workflows.results(workflow.id)
with open(f"{foldername}/{workflow.name}_results.json", "w") as fp:
    fp.write(tso_results.model_dump_json(indent=2))

# Optimized molecule:
optimized_molecule = tso_results.get_artifact("optimized-molecule")
print(optimized_molecule)

# Download:
with open(f"{foldername}/{workflow.name}_results.zip", "wb") as fp:
    fp.write(prom.workflows.download(workflow.id))
