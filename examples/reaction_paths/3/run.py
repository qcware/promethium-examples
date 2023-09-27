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
C        -5.01984        3.25732        0.26860
N        -5.22839        4.59181        0.26874
C        -4.13916        5.40298        0.29654
N        -3.84370        2.58834        0.29547
H        -5.91590        2.64320        0.24386
C        -2.81180        3.45438        0.32033
N        -1.47672        3.16085        0.34463
C        -2.86821        4.84032        0.32356
H        -4.31111        6.47120        0.29481
N        -1.60682        5.38518        0.35290
C        -0.79465        4.34845        0.36405
H         0.28657        4.38753        0.38438
H        -1.06676        2.22989        0.33983
O        -0.58794        0.52174        0.23170
H        -0.04106       -0.25240        0.01561
H        -3.49630        0.74509        0.30278
O        -3.18303       -0.18181        0.40960
H        -1.47988        0.09853        0.30118
H        -3.96444       -0.60633        0.80218
""").decode("utf-8")

product = base64.b64encode(b"""
C        -4.98983        3.18813        0.26429
N        -5.23516        4.46846        0.26853
C        -4.11673        5.30154        0.29630
N        -3.74153        2.62888        0.28051
H        -5.80795        2.44975        0.24592
C        -2.64294        3.42587        0.30816
N        -1.36414        3.18946        0.33320
C        -2.84641        4.87876        0.31594
H        -4.32519        6.36698        0.30428
N        -1.62977        5.48417        0.34774
C        -0.81003        4.47105        0.35751
H         0.28394        4.60016        0.38383
H        -0.83448        1.38557        0.27753
O        -0.73691        0.40616        0.23951
H         0.21680        0.31445        0.07490
H        -3.63828        1.61046        0.31017
O        -3.37541       -0.04224        0.46049
H        -2.39001       -0.08344        0.36256
H        -3.56509       -0.95791        0.72937
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

