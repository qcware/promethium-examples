import base64
import json
import httpx
import os

from promethium_sdk.utils import BYTES_PER_GB, wait_for_workflows_to_complete

# This example expects that your API credentials have been configured and
# stored as an environment variable.
#
# If you do not have the SDK installed, remove or comment out the references
# to the `BYTES_PER_GB` variable and `wait_for_workflows_to_complete` function.

# Estimated runtimes:
#   Nemorexant
#     without optional fine DFT filter stage
#       - Compute time: ~1 hr
#       - Elapsed time: <15 min
#     with optional fine DFT filter stage
#       - Compute time: ~1 hr
#       - Elapsed time: <15 min

# Specify API base URL and GPU resource type
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

# Specify output folder
foldername = "output"
if not os.path.exists(foldername):
    os.makedirs(foldername)

# Set header to use your API key
headers = {
    "x-api-key": os.environ["PM_API_KEY"],
    "accept": "application/json",
    "content-type": "application/json",
}

# Instantiate the HTTPX client
client = httpx.Client(base_url=base_url, headers=headers)

# Specify the input file contents and prepare (base64encode) for API submission
# Molecule: Nemorexant
input_mol = base64.b64encode(b"CC1=C(C=CC2=C1N=C(N2)C3(CCCN3C(=O)C4=C(C=CC(=C4)OC)N5N=CC=N5)C)Cl")
input_mol = input_mol.decode("utf-8")

# Should we add a second fine DFT filter?
fine_dft = True

# CS (Conformer Search) workflow configuration
workflow_name = "nemorexant_api_cs"
job_params = {
    "name": workflow_name,
    "version": "v1",
    "kind": "ConformerSearch",
    "parameters": {
        "molecule": {
            "base64data": input_mol,
            "filetype": "smi"
        },
        "params": {
            "confgen_max_n_conformers": 1000,
            "confgen_rmsd_threshold": 0.3,
            "charge": 0,
            "multiplicity": 1
        },
        "filters": [
            {
                "filtertype": "ForceField",
                "params": {
                    "forcefield_type": "MMFF",
                    "do_geometry_optimization": True,
                    "max_n_conformers": 150,
                    "energy_threshold": 15,
                    "rmsd_threshold": 0.3,
                    "coulomb_distance_threshold": 0.005,
                },
            },
            {
                "filtertype": "ANI",
                "params": {
                    "method": "ANI-2x",
                    "do_geometry_optimization": True,
                    "max_n_conformers": 25,
                    "energy_threshold": 10,
                    "distance_threshold": 0.005,
                },
            },
            {
                "filtertype": "DFT",
                "params": {
                    "do_geometry_optimization": True,
                    "maxiter": 15,
                    "g_convergence": 0.001,
                    "energy_threshold": 5,
                    "distance_threshold": 0.005
                },
                "system": {
                    "params": {
                        "methodname": "b3lyp-d3",
                        "basisname": "def2-svp",
                        "jkfit_basisname": "def2-universal-jkfit",
                        "xc_grid_scheme": "SG1",
                        "pcm_epsilon": 80.4,
                        "pcm_spherical_npoint": 110
                    }
                },
                "hf": {
                    "params": {
                        "g_convergence": 0.000001
                    }
                },
                "jk_builder": {
                    "type": "core_dfjk",
                    "params": {}
                },
            },
        ],
    },
    "resources": {"gpu_type": gpu_type},
}

# Optionally add the fine DFT filter stage
fine_dft_filter = {
    "filtertype": "DFT",
    "params": {
        "do_geometry_optimization": False,
        "energy_threshold": 4,
        "distance_threshold": 0.005
    },
    "system": {
        "params": {
            "methodname": "wb97m-v",
            "basisname": "def2-tzvp",
            "jkfit_basisname": "def2-universal-jkfit",
            "xc_grid_scheme": "SG1",
            "pcm_epsilon": 80.4,
            "pcm_spherical_npoint": 110
        }
    },
    "hf": {
        "params": {
            "g_convergence": 0.000001
        }
    },
    "jk_builder": {
        "type": "core_dfjk",
        "params": {}
    },
}

if fine_dft:
    job_params["parameters"]["filters"].append(fine_dft_filter)

# Add metadata only if environment variables exist
metadata = {}
workflow_timeout = os.getenv("PM_WORKFLOW_TIMEOUT")
task_timeout = os.getenv("PM_TASK_TIMEOUT")

if workflow_timeout:
    metadata["workflow_timeout"] = int(workflow_timeout)
if task_timeout:
    metadata["task_timeout"] = int(task_timeout)
if metadata:
    job_params["metadata"] = metadata

# Estimate required GPU memory for workflow
payload = job_params
response = client.post("/v0/workflows/memory", json=payload).json()
cs_memory = response["prediction_bytes"]
cs_memory_percentile = response["percentile_prediction_bytes"]
print(f"Estimated GPU memory usage: {cs_memory/BYTES_PER_GB} GB")
print(
    "Estimated GPU memory usage range: "
    f"({cs_memory_percentile['0.025']/BYTES_PER_GB}, "
    f"{cs_memory_percentile['0.975']/BYTES_PER_GB}) GB")

# Submit a CS workflow using the above configuration
jobname = payload["name"]
response = client.post("/v0/workflows", json=payload).json()
with open(os.path.join(foldername, f"{jobname}_submitted.json"), "w") as fp:
    fp.write(json.dumps(response))
workflow_id = response["id"]
print(f"Workflow {jobname} submitted with id: {workflow_id}")

# Wait for the workflow to finish
workflow = wait_for_workflows_to_complete(
    client=client,
    workflow_ids=[workflow_id],
    log_events=["STATE_CHANGES"],
    timeout=3600,
)[workflow_id]

# Get the status and elapsed time
response = client.get(f"v0/workflows/{workflow_id}").json()
with open(os.path.join(foldername, f"{jobname}_status.json"), "w") as fp:
    fp.write(json.dumps(response))
elapsed_time = response["duration_seconds"]
print(f"Workflow {jobname} completed with status: {workflow['status']}")
print(f"Workflow completed in {elapsed_time:.2f}s")

# Obtain the numeric results
response = client.get(f"/v0/workflows/{workflow_id}/results", headers=headers).json()
with open(os.path.join(foldername, f"{jobname}_results.json"), "w") as fp:
    fp.write(json.dumps(response))

# Extract and print the conformers
conformers = response["results"]["artifacts"]["conformers"]["base64data"]
print("Conformers:\n====================\n")
print(f'{base64.b64decode(conformers).decode("utf-8")}')

# Download results
response = client.get(
    f"/v0/workflows/{workflow_id}/results/download", follow_redirects=True
)
with open(os.path.join(foldername, f"{jobname}_results.zip"), "wb") as fp:
    fp.write(response.content)
