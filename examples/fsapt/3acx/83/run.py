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

monomerA = base64encode(
"""44

C  48.671 21.557 53.684
H  47.823 22.241 53.598
H  48.289 20.572 53.954
H  49.180 21.501 52.722
C  49.596 22.100 54.803
O  49.116 22.807 55.689
N  50.903 21.802 54.711
H  51.219 21.214 53.952
C  51.944 22.268 55.631
H  51.555 22.215 56.650
C  53.139 21.324 55.530
H  53.585 21.344 54.534
H  53.918 21.594 56.243
H  52.849 20.294 55.743
C  52.409 23.719 55.391
O  53.117 24.241 56.251
N  52.051 24.344 54.253
H  51.460 23.865 53.588
C  52.575 25.654 53.839
H  53.662 25.547 53.818
H  52.310 26.429 54.559
H  52.218 25.937 52.849
C  58.425 25.417 46.737
H  59.127 25.063 45.980
H  58.915 26.198 47.317
H  57.548 25.828 46.238
C  58.065 24.222 47.647
O  58.867 23.297 47.759
N  56.856 24.232 48.235
H  56.243 25.025 48.106
C  56.344 23.138 49.057
H  57.158 22.808 49.705
C  55.221 23.662 49.948
H  54.336 23.939 49.374
H  54.931 22.897 50.664
H  55.538 24.531 50.524
C  55.891 21.911 48.246
O  56.118 20.792 48.709
N  55.316 22.126 47.044
H  55.125 23.074 46.745
C  55.057 21.069 46.059
H  54.467 20.298 46.551
H  55.991 20.625 45.711
H  54.499 21.450 45.203
"""
)

monomerB = base64encode(
"""39

C  56.282 16.378 57.621
C  56.834 15.837 56.524
C  58.279 22.417 53.598
C  57.370 22.160 52.579
C  58.747 21.380 54.394
C  56.925 20.858 52.361
C  58.292 20.088 54.185
C  56.429 17.916 51.785
C  55.922 16.622 51.676
C  56.729 17.578 54.142
C  56.063 15.397 55.288
C  55.187 12.287 51.991
C  54.688 11.792 53.357
C  56.040 13.558 52.114
O  55.220 14.572 52.679
C  57.361 19.807 53.181
C  56.838 18.417 53.025
C  56.221 16.278 54.049
C  55.805 15.806 52.799
H  56.889 16.671 58.467
H  55.215 16.540 57.696
H  57.907 15.694 56.488
H  58.628 23.427 53.768
H  57.013 22.975 51.969
H  59.462 21.581 55.180
H  56.226 20.680 51.560
H  58.681 19.305 54.820
H  56.499 18.526 50.895
H  55.597 16.245 50.723
H  57.004 17.959 55.114
H  54.998 15.320 55.515
H  56.396 14.385 55.052
H  54.336 12.479 51.335
H  55.773 11.505 51.508
H  54.050 12.532 53.844
H  55.518 11.575 54.031
H  56.413 13.855 51.133
H  56.912 13.374 52.744
H  54.103 10.878 53.251
"""
)

job_params = {
    "name": "fsapt-test",
    "version": "v1",
    "kind": "FSAPTCalculation",
    "parameters": {
        "molecule_a": {
            "base64data": monomerA,
            "filetype": "xyz",
            "params": {
                "charge": 0,
            }
        },
        "molecule_b": {
            "base64data": monomerB,
            "filetype": "xyz",
            "params": {
                "charge": 0,
            }
        },
        "system": {
            "params": {
                "methodname": "hf",
                "basisname": "jun-cc-pvdz",
                "jkfit_basisname": "jun-cc-pvdz-jkfit",
                "k_grid_scheme": "GRID1",
                "threshold_pq": 1e-12
            }
        },
        "jk_builder": {
#            "type": "core_dfjk",
            "type": "dfj_grid_k",
#            "type": "numerical_jk",
            "params": {}
        },
        "hf": {
            "params": {
                "g_convergence": 1.0e-6
            }
        }
    },
    "resources": {
        "gpu_type": "a100",
        "gpu_count": 1
    }
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

response = client.get(
    f"/v0/workflows/{workflow_id}/results/download", follow_redirects=True
)
with open(os.path.join(foldername, f"{jobname}_results.zip"), "wb") as fp:
    fp.write(response.content)

response = client.get(f"/v0/workflows/{workflow_id}/results").json()

Eelst = 627.5095 * response['results']['fsapt']['scalars']['Eelst']
Eexch = 627.5095 * response['results']['fsapt']['scalars']['Eexch']
EindAB = 627.5095 * response['results']['fsapt']['scalars']['EindAB']
EindBA = 627.5095 * response['results']['fsapt']['scalars']['EindBA']
Edisp = 627.5095 * response['results']['fsapt']['scalars']['Edisp']
Esapt = 627.5095 * response['results']['fsapt']['scalars']['Esapt']

print('')
print('SAPT Analysis (kcal / mol)')
print('')
print('    Elst     Exch    IndAB    IndBA     Disp    Total')
print('%8.3lf %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf' % (Eelst, Eexch, EindAB, EindBA, Edisp, Esapt))
print('')
