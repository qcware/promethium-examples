import json
import os

import httpx
from promethium_sdk.utils import (
    base64encode,
    wait_for_workflows_to_complete,
)

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")
workflow_timeout = int(os.getenv("PM_WORKFLOW_TIMEOUT", 864000))
task_timeout = int(os.getenv("PM_TASK_TIMEOUT", 864000))
dir_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
)

if not os.path.exists(foldername):
    os.makedirs(foldername)

headers = {
    "x-api-key": os.environ["PM_API_KEY"],
    "accept": "application/json",
    "content-type": "application/json",
}

client = httpx.Client(base_url=base_url, headers=headers)

n = 4
workflow_ids = []

for i in range(1, n + 1):
    with open(os.path.join(dir_path, f"{i}/reactant.xyz"), "r") as fp:
        reactant = base64encode(bytes(fp.read(), "utf-8"))
    with open(os.path.join(dir_path, f"{i}/product.xyz"), "r") as fp:
        product = base64encode(bytes(fp.read(), "utf-8"))

    job_params = {
        "name": f"api-ts-opt-{i}",
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
        "metadata": {"workflow_timeout": workflow_timeout, "task_timeout": task_timeout},
    }

    payload = job_params
    jobname = payload["name"]
    print(f"Submitting {jobname}...", end="")
    response = client.post("/v0/workflows", json=payload)
    with open(f"{foldername}/{jobname}_submitted.json", "w") as fp:
        fp.write(json.dumps(response.json()))
    workflow_id = response.json()["id"]
    workflow_ids.append(workflow_id)
    print("done!")

workflows = wait_for_workflows_to_complete(
    client=client,
    workflow_ids=workflow_ids,
    log_events=["STATE_CHANGES"],
    timeout=3600,
)
print(f"Workflow completed with statuses: {workflows}")

for i, workflow_id in enumerate(workflow_ids):
    response = client.get(f"/v0/workflows/{workflow_id}").json()
    with open(f"{foldername}/{i}_status.json", "w") as fp:
        fp.write(json.dumps(response))
    name = response["name"]
    timetaken = response["duration_seconds"]
    print(f"Experiment: {i}, Name: {name}, time taken: {timetaken:.2f}s")

    response = client.get(f"/v0/workflows/{workflow_id}/results").json()
    with open(f"{foldername}/{i}_results.json", "w") as fp:
        fp.write(json.dumps(response))

    response = client.get(
        f"/v0/workflows/{workflow_id}/results/download", follow_redirects=True
    )
    with open(f"{foldername}/{i}_results.zip", "wb") as fp:
        fp.write(response.content)
