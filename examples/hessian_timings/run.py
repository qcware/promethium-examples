import requests
import base64
import json
import itertools
import httpx
import os

from utils import wait_for_workflows_to_complete

foldername = 'output'
url = "https://api.promethium-dev.qcware.com/v0/workflows"

mol = base64.b64encode(b"""
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

mol = mol.decode("utf-8")

job_params = {
    "name": f"melarsoprol_api_hessian",
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {
            "base64data": mol,
            "filetype": "xyz"
        },
        "system": {
            "params": {
                "basisname": 'def2-svp',
                "jkfit_basisname": "def2-universal-jkfit",
                "xc_functional_name": 'b3lyp',
                "xc_grid_scheme": "SG1"
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
                "print_hessian_timings": True
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
                "g_convergence": 1.0e-3
            },
            "outputs": {
                "gradient": True,
                "vibrational_frequencies": True
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
energy = response['results']['optimization']['energy']
print(energy)

url = f'https://api.promethium-dev.qcware.com/v0/workflows/{workflow_id}/results/download'
response = requests.get(url, headers=headers, stream=True)
with open(f'{foldername}/{jobname}_results.zip', 'wb') as fp:
    for chunk in response.iter_content(chunk_size=128):
        fp.write(chunk)

