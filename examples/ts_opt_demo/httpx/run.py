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
response.raise_for_status()
with open(f"{foldername}/{jobname}_submitted.json", "w") as fp:
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
with open(f"{foldername}/{jobname}_status.json", "w") as fp:
    fp.write(json.dumps(response))
name = response["name"]
timetaken = response["duration_seconds"]
print(f"Name: {name}, time taken: {timetaken:.2f}s")

response = client.get(f"/v0/workflows/{workflow_id}/results").json()
with open(f"{foldername}/{jobname}_results.json", "w") as fp:
    fp.write(json.dumps(response))

response = client.get(
    f"/v0/workflows/{workflow_id}/results/download", follow_redirects=True
)
with open(f"{foldername}/{jobname}_results.zip", "wb") as fp:
    fp.write(response.content)
