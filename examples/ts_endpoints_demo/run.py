import base64
import json
import httpx
import os

from utils import wait_for_workflows_to_complete

foldername = 'output'
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

reactant = base64.b64encode(b"""
 C 0.797293840 1.081303780 -0.164555970
 C -0.547182890 0.998873790 0.574238880
 H -0.395761920 0.541241890 1.549831680
 H -0.946053810 2.004760590 0.703269860
 C -1.496643690 0.140619970 -0.215631960
 O -1.541888690 -1.054995780 -0.095877980
 O 1.220317750 -0.170981970 -0.648934870
 O 1.345670720 -1.049579780 0.455224910
 H 0.495284900 -1.516554690 0.425610910
 H 1.552030680 1.511683690 0.496874900
 H 0.720901850 1.693360650 -1.064286780
 H -2.139998560 0.645187870 -0.958893800 
""").decode("utf-8")

product = base64.b64encode(b"""
 C -1.480477590 0.370142220 -0.164123070
 C -0.251557300 1.224758920 0.164042060
 H 0.085104930 1.819910830 -0.680028190
 H -0.422626420 1.873975670 1.018131660
 C 0.792370180 0.146459590 0.462201780
 O 1.718927540 0.129648000 -0.577786030
 O -0.957214940 -0.918376860 -0.436228060
 O 0.062106850 -1.054181550 0.552944200
 H 2.285253460 -0.639917330 -0.473943670
 H -2.007051530 0.682219430 -1.062658090
 H -2.172374500 0.318049500 0.679016970
 H 1.279126720 0.240880770 1.435315840 
""").decode("utf-8")

job_params = {
    "name": f"api_ts_opt",
    "version": "v1",
    "kind": "TransitionStateOptimizationFromEndpoints",
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
                "rk_thresh": 1.0e-2,
                "integrator": "rk45",
                "dt": 0.01,
                "nbeads": 11
            }
        },
        "neb": {
            "params": {
                "force_constant_upper": 0.10,
                "force_constant_lower": 0.01
            }
        },
        "fire": {
            "params": {
                "g_convergence": 1.0e-2,
                "dt_start": 0.5,
                "alpha_start": 0.25
            }
        },
        "prfo": {
            "params": {
                "eigenvector_convergence": 1.0e-4,
                "strict_convergence": True
            },
            "outputs": {
                "vibrational_frequencies": True
            }
        }
    },
    "resources": {
        "gpu_type": gpu_type
    },
}

headers = {
    "x-api-key" : os.environ['PM_API_KEY'],
    "accept": "application/json",
    "content-type": "application/json"
}

client = httpx.Client(base_url=base_url, headers=headers)

payload = job_params
jobname = payload['name']
print(f'Submitting {jobname}...', end='')
response = client.post("/v0/workflows", json=payload)
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

response = client.get(f'/v0/workflows/{workflow_id}').json()
with open(f'{foldername}/{jobname}_status.json', 'w') as fp:
    fp.write(json.dumps(response))
name = response['name']
timetaken = response['duration_seconds']
print(f'Name: {name}, time taken: {timetaken:.2f}s')

response = client.get(f'/v0/workflows/{workflow_id}/results').json()
with open(f'{foldername}/{jobname}_results.json', 'w') as fp:
    fp.write(json.dumps(response))

response = client.get(f'/v0/workflows/{workflow_id}/results/download', follow_redirects=True)
with open(f'{foldername}/{jobname}_results.zip', 'wb') as fp:
    fp.write(response.content)
