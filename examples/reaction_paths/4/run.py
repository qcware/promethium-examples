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
C        -5.19650        3.54934        0.23974
N        -5.31356        4.88460        0.40456
C        -4.17171        5.61782        0.45442
N        -4.06895        2.80935        0.11573
H        -6.13294        2.99916        0.20399
C        -2.98051        3.60184        0.16675
N        -1.66933        3.22867        0.06819
C        -2.94305        4.97901        0.33160
H        -4.26901        6.68703        0.58858
N        -1.64909        5.44115        0.34025
C        -0.90952        4.36377        0.18163
H         0.17142        4.33182        0.14003
H        -1.31099        2.28554       -0.06129
O        -0.36917        0.79784       -0.16849
H         0.25611        0.22664       -0.64710
H        -3.96498        0.97639        0.49791
O        -4.06196        0.00425        0.61718
H        -0.76761        0.13089        0.44646
H        -4.83772       -0.17435        0.05848
O        -1.67848       -0.99278        1.34900
H        -1.87030       -1.48746        2.16397
H        -2.59534       -0.72372        1.08614
""").decode("utf-8")

product = base64.b64encode(b"""
C        -5.11866        3.37149        0.38742
N        -5.33560        4.71032        0.44082
C        -4.23187        5.51508        0.39666
N        -3.93467        2.78103        0.29089
H        -5.98404        2.71954        0.42894
C        -2.89100        3.54584        0.24649
N        -1.61486        3.13538        0.15269
C        -2.96710        4.93077        0.29692
H        -4.36154        6.58821        0.44320
N        -1.68782        5.36242        0.23296
C        -0.88057        4.28091        0.15805
H         0.20275        4.32989        0.10910
H        -0.84869        1.63942        0.10204
O        -0.42358        0.74961       -0.07444
H         0.18370        1.03355       -0.78045
H        -3.82398        1.76479        0.26935
O        -4.13126        0.28836        0.42079
H        -1.29384       -0.37965        0.78030
H        -4.55878       -0.52979        0.09386
O        -1.94844       -0.89006        1.33091
H        -1.33918       -1.25605        1.99699
H        -3.34416       -0.15427        0.85423
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

