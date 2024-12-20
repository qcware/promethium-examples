import json
import httpx
import os

from promethium_sdk.utils import (
    base64encode,
    wait_for_workflows_to_complete,
)

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
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
""")

job_params = {
    "name": "melarsoprol_api_hessian",
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
                "print_hessian_timings": True,
            },
        },
        "pes": {
            "params": {"coordinate_system_name": "redundant"},
        },
        "optimization": {
            "params": {"maxiter": 200, "g_convergence": 1.0e-3},
            "outputs": {"gradient": True, "vibrational_frequencies": True},
        },
    },
    "resources": {"gpu_type": gpu_type},
}

headers = {
    "x-api-key": os.environ["PM_API_KEY"],
    "accept": "application/json",
    "content-type": "application/json",
}

client = httpx.Client(base_url=base_url, headers=headers)

payload = job_params
jobname = payload["name"]
print(f"Submitting {jobname}...", end="")
response = client.post("/v0/workflows", json=payload)
with open(os.path.join(foldername, f"{jobname}_submitted.json"), "w") as fp:
    fp.write(json.dumps(response.json()))
workflow_id = response.json()["id"]
print("done!")

workflow = wait_for_workflows_to_complete(
    client=client,
    workflow_ids=[workflow_id],
    log_events=["STATE_CHANGES"],
    timeout=3600,
)[workflow_id]
print(f"Workflow completed with status: {workflow['status']}")

response = client.get(f"/v0/workflows/{workflow_id}").json()
with open(os.path.join(foldername, f"{jobname}_status.json"), "w") as fp:
    fp.write(json.dumps(response))
name = response["name"]
timetaken = response["duration_seconds"]
print(f"Name: {name}, time taken: {timetaken:.2f}s")

response = client.get(f"/v0/workflows/{workflow_id}/results").json()
with open(os.path.join(foldername, f"{jobname}_results.json"), "w") as fp:
    fp.write(json.dumps(response))
energy = response["results"]["optimization"]["energy"]
print(energy)

response = client.get(
    f"/v0/workflows/{workflow_id}/results/download", follow_redirects=True
)
with open(os.path.join(foldername, f"{jobname}_results.zip"), "wb") as fp:
    fp.write(response.content)
