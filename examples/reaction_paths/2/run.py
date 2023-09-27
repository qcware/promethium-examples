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
C        -4.89600        3.13667        0.18599
N        -5.20658        4.44927        0.28399
C        -4.18308        5.33999        0.36983
N        -3.67198        2.56418        0.16254
H        -5.74098        2.45710        0.11767
C        -2.71402        3.50477        0.24897
N        -1.36211        3.30550        0.25567
C        -2.87246        4.87684        0.35281
H        -4.43799        6.38844        0.44918
N        -1.65135        5.50648        0.42052
C        -0.76615        4.53225        0.35968
H         0.30932        4.64938        0.38716
H        -0.91084        2.39782        0.20090
O        -1.38484        0.49184        0.19096
H        -1.40230       -0.47228        0.30967
H        -2.33723        0.71470        0.14426
""").decode("utf-8")

product = base64.b64encode(b"""
C        -4.78169        3.02610        0.18800
N        -5.15663        4.27252        0.27026
C        -4.13016        5.21566        0.35530
N        -3.48234        2.60074        0.17898
H        -5.52090        2.21159        0.11809
C        -2.47689        3.50884        0.26205
N        -1.18313        3.39264        0.27928
C        -2.82309        4.92757        0.35703
H        -4.44824        6.25160        0.42513
N        -1.66974        5.64443        0.43022
C        -0.75474        4.71630        0.38137
H         0.32222        4.94621        0.41820
H        -1.11940        1.27004        0.15463
O        -1.70252        0.48056        0.16001
H        -1.06726       -0.23451        0.33467
H        -3.23407        1.61268        0.12658
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

