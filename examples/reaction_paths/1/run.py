import requests
import base64
import json
import itertools
import httpx
import os

from utils import wait_for_workflows_to_complete

foldername = 'output'
url = "https://api.promethium-dev.qcware.com/v0/workflows"

reactant = base64.b64encode(b"""
C        -4.89447        2.95468       -0.04569
N        -5.18807        4.23094        0.29315
C        -4.15316        5.07515        0.54685
N        -3.67793        2.38371       -0.17142
H        -5.74610        2.30900       -0.24082
C        -2.70852        3.27247        0.09298
N        -1.36234        3.05357        0.06632
C        -2.84889        4.60324        0.45054
H        -4.39460        6.09445        0.81741
N        -1.61900        5.18940        0.63970
C        -0.74831        4.23026        0.40114
H         0.32853        4.32554        0.45406
H        -0.91827        2.17688       -0.16069
""").decode("utf-8")

product = base64.b64encode(b"""
C        -4.67137        2.88063       -0.05953
N        -5.04669        4.08716        0.25829
C        -4.02077        4.99437        0.52800
N        -3.37170        2.45921       -0.14346
H        -5.41091        2.09619       -0.28875
C        -2.36540        3.33256        0.11701
N        -1.07454        3.22012        0.11820
C        -2.71371        4.70842        0.48110
H        -4.33826        5.99839        0.79324
N        -1.56262        5.39912        0.69630
C        -0.64605        4.49728        0.47477
H         0.43039        4.71604        0.56101
H        -3.13953        1.50979       -0.39266
""").decode("utf-8")

job_params = {
    "name": f"api_ts_opt",
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
                "basisname": 'def2-svp',
                "jkfit_basisname": "def2-universal-jkfit",
                "xc_functional_name": 'b3lyp',
                "xc_grid_scheme": "SG1",
                "threshold_pq": 1.0e-12
            },
        },
        "hf": {
            "params": {
                "multiplicity": 1,
                "charge": 0,
                "g_convergence": 1.0e-6,
                "print_level": 0
            },
        },
        "pes": {
            "params": {
                "coordinate_system_name": "redundant"
            },
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
                "nbeads": 11
            },
        },
        "neb": {
            "params": {
                "force_constant_upper": 0.10,
                "force_constant_lower": 0.01
            },
        },
        "fire": {
            "params": {
                "g_convergence": 5.0e-3,
                "dt_start": 0.5,
                "alpha_start": 0.25
            },
        },
    },
    "resources": {
        "gpu_type": "v100"
    },
}

headers = {
    "x-api-key" : os.environ['PM_API_KEY'],
    "accept": "application/json",
    "content-type": "application/json"
}

client = httpx.Client(base_url='https://api.promethium-dev.qcware.com', headers=headers)

payload = job_params
jobname = payload['name']
print(f'Submitting {jobname}...', end='')
response = requests.post(url, json=payload, headers=headers)
with open(f'{foldername}/{jobname}_submitted.json', 'w') as fp:
    fp.write(json.dumps(response.json()))
workflow_id = response.json()["id"]
print('done!')

workflow = wait_for_workflows_to_complete(
    client=client,
    workflow_ids=[workflow_id],
    log_events=["STATE_CHANGES"],
    timeout=3600,
)[workflow_id]
print(f"Workflow completed with status: {workflow['status']}")

url = f'https://api.promethium-dev.qcware.com/v0/workflows/{workflow_id}'
response = requests.get(url, headers=headers).json()
with open(f'{foldername}/{jobname}_status.json', 'w') as fp:
    fp.write(json.dumps(response))
name = response['name']
timetaken = response['duration_seconds']
print(f'Name: {name}, time taken: {timetaken:.2f}s')

url = f'https://api.promethium-dev.qcware.com/v0/workflows/{workflow_id}/results'
response = requests.get(url, headers=headers).json()
with open(f'{foldername}/{jobname}_results.json', 'w') as fp:
    fp.write(json.dumps(response))

url = f'https://api.promethium-dev.qcware.com/v0/workflows/{workflow_id}/results/download'
response = requests.get(url, headers=headers, stream=True)
with open(f'{foldername}/{jobname}_results.zip', 'wb') as fp:
    for chunk in response.iter_content(chunk_size=128):
        fp.write(chunk)

