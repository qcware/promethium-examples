import os

from promethium_sdk.utils import base64encode
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    # This requires an SDK version >= 0.3.12 for the SCF properties.
    CreateSinglePointCalculationWorkflowRequest,
)

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

input_mol = base64encode(
    """9

    O   -1.510407226976    0.757898746844    0.000000000000
    O   -0.553334234073   -1.306832947272    0.000000000000
    C    0.851836372408    0.670262334922    0.000000000000
    C   -0.435392872548   -0.091344744168    0.000000000000
    C    2.037631538003    0.030293859895    0.000000000000
    H    0.778714996763    1.768162197756    0.000000000000
    H    2.070317763114   -1.070327443612    0.000000000000
    H    2.990077611988    0.580280001156    0.000000000000
    H   -2.306286818048    0.180092981979    0.000000000000
""")

job_params = {
    "name": "spc_atomic_charges",
    "version": "v1",
    "kind": "SinglePointCalculation",
    "parameters": {
        "molecule": {"base64data": input_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": "def2-svp",
                "methodname": "hf",
                "xc_grid_scheme": "SG2",
            }
        },
        "hf": {
            "params": {"charge": 0, "multiplicity": 1, "g_convergence": 0.000001},
        },
        "scf_properties": {
            "outputs": [
                {"type": "atomic_charges", "analysis_method": "mulliken"},
                {"type": "atomic_charges", "analysis_method": "lowdin"},
                {"type": "atomic_charges", "analysis_method": "iao"},
                {"type": "atomic_charges", "analysis_method": "resp"},
            ],
        },
    },
    "resources": {"gpu_type": gpu_type},
}

prom = PromethiumClient()
spc_payload = CreateSinglePointCalculationWorkflowRequest(**job_params)
spc_workflow = prom.workflows.submit(spc_payload)
print(f"Workflow {spc_workflow.name} submitted with id: {spc_workflow.id}")

prom.workflows.wait(spc_workflow.id)

spc_workflow = prom.workflows.get(spc_workflow.id)
print(f"Workflow {spc_workflow.name} completed with status: {spc_workflow.status}")
print(f"Workflow completed in {spc_workflow.duration_seconds:.2f}s")

spc_results = prom.workflows.results(spc_workflow.id)
with open(os.path.join(foldername, f"{spc_workflow.name}_results.json"), "w") as fp:
    fp.write(spc_results.model_dump_json(indent=2))

# Download results:
with open(os.path.join(foldername, f"{spc_workflow.name}_results.zip"), "wb") as fp:
    fp.write(prom.workflows.download(spc_workflow.id))

# Extract and print the atomic charges contained in the numeric results:
atomic_charges = spc_results.results["scf_properties"]["atomic_charges"]
analysis_methods = [data["analysis_method"] for data in atomic_charges]
analysis_results = [data["atomic_charges"] for data in atomic_charges]

print()
print(" Atom |" + " |".join([f"{k:>12s}" for k in analysis_methods]))
print("------+" + "+".join(["-------------" for k in analysis_methods]))
for n, vals in enumerate(zip(*analysis_results)):
    print(f"  {n:3d} |" + " |".join([f"{v:12.8f}" for v in vals]))

# This script will print a table which looks like this (with minor numerical differences):
"""
 Atom |    mulliken |      lowdin |         iao |        resp
------+-------------+-------------+-------------+-------------
    0 | -0.37437257 | -0.12756925 | -0.53481521 | -0.65778992
    1 | -0.41297900 | -0.28500846 | -0.54429049 | -0.61056609
    2 | -0.23633031 | -0.09817325 | -0.20831543 | -0.29427909
    3 |  0.51611239 |  0.22104588 |  0.63909487 |  0.84930926
    4 |  0.01203033 |  0.05216236 | -0.18156946 | -0.30860144
    5 |  0.08354477 |  0.03970350 |  0.14808050 |  0.18337875
    6 |  0.10109182 |  0.04459825 |  0.15936747 |  0.20354619
    7 |  0.08306289 |  0.03691336 |  0.14638526 |  0.19056022
    8 |  0.22783968 |  0.11632762 |  0.37606249 |  0.44444211
"""