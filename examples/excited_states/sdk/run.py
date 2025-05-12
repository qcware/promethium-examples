import copy
import json
import os

from promethium_sdk.utils import base64encode
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    # This requires an SDK version >= 0.4.5 for the excited_states settings supporting RPA methods,
    # and the additional result fields.
    CreateSinglePointCalculationWorkflowRequest,
)

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

mol = base64encode("""10

    C         25.72300       29.68500       26.90100
    C         25.51000       29.88900       25.49000
    C         26.07700       30.59500       27.82800
    C         25.16300       28.92900       24.60400
    H         25.62000       28.64500       27.18200
    H         25.33300       30.87700       25.08600
    H         26.26500       30.17800       28.85200
    H         26.32100       31.69500       27.63100
    H         24.81000       29.04000       23.56900
    H         25.10400       27.88700       24.94600"""
)

spc_rrpa_name = "spc_rrpa_example"
job_params_rrpa = {
    "name": spc_rrpa_name,
    "version": "v1",
    "kind": "SinglePointCalculation",
    "parameters": {
        "molecule": {"base64data": mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": "def2-svp",
                "jkfit_basisname": "def2-universal-jkfit",
                "methodname": "b3lyp",
                "xc_grid_scheme": "SG0"
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
        "jk_builder": {
            "type": "core_dfjk",
            "params": {}
        },
        "excited_states": {
            "type": "rrpa",
            "params": {
                "nmax": 50,
                "S_inds": [0, 2],
                "maxiter": 70,
                "S_nstates": [1, 3],
                "gradient_target": 1,
                "gradient_target_spin": 0
            },
            "outputs": {
                "gradient": False
            }
        },
    },
    "resources": {"gpu_type": gpu_type},
}

# Use the same settings as RRPA but switch the method type
spc_rcis_name = "spc_rcis_example"
job_params_rcis = copy.deepcopy(job_params_rrpa)
job_params_rcis["name"] = spc_rcis_name
job_params_rcis["parameters"]["excited_states"]["type"] = "rcis"

# Instantiate the Promethium client and submit two SPC workflows using RPA and CIS settings
prom = PromethiumClient()
spc_rrpa_payload = CreateSinglePointCalculationWorkflowRequest(**job_params_rrpa)
spc_rrpa_workflow = prom.workflows.submit(spc_rrpa_payload)
print(f"Workflow {spc_rrpa_workflow.name} submitted with id: {spc_rrpa_workflow.id}")
spc_rcis_payload = CreateSinglePointCalculationWorkflowRequest(**job_params_rcis)
spc_rcis_workflow = prom.workflows.submit(spc_rcis_payload)
print(f"Workflow {spc_rcis_workflow.name} submitted with id: {spc_rcis_workflow.id}")

# Wait for the workflows to finish and download the results
for workflow_id in [spc_rrpa_workflow.id, spc_rcis_workflow.id]:
    prom.workflows.wait(workflow_id)
    workflow = prom.workflows.get(workflow_id)
    print()
    print(f"Workflow {workflow.name} completed with status {workflow.status} in {workflow.duration_seconds:.2f}s")

    workflow_results = prom.workflows.results(workflow.id)
    with open(os.path.join(foldername, f"{workflow.name}_results.json"), "w") as fp:
        fp.write(workflow_results.model_dump_json(indent=2))
    with open(os.path.join(foldername, f"{workflow.name}_results.zip"), "wb") as fp:
        fp.write(prom.workflows.download(workflow.id))

    print(f"Results from {workflow.name}:")
    print(json.dumps(workflow_results.results["excited_states"], indent=2))

