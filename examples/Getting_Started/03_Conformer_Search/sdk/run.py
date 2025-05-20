import copy
import os

from promethium_sdk.utils import base64encode, BYTES_PER_GB
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateConformerSearchWorkflowRequest,
)
from promethium_sdk.utils import (
    base64encode,
)

# This example expects that your API credentials have been configured and
# stored in a .promethium.ini file.
# If that hasn't been completed, see the following instructions:
# https://github.com/qcware/promethium-examples/tree/main#configuring-your-api-credentials

# Estimated runtimes:
#   Nemorexant
#     without optional fine DFT filter stage
#       - Compute time: ~1 hr
#       - Elapsed time: <15 min
#     with optional fine DFT filter stage
#       - Compute time: ~1 hr
#       - Elapsed time: <15 min

# Specify GPU resource type
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

# Specify output folder
foldername = "output"
if not os.path.exists(foldername):
    os.makedirs(foldername)

# Specify the input file contents and prepare (base64encode) for API submission
# Molecule: Nemorexant
input_mol = base64encode("CC1=C(C=CC2=C1N=C(N2)C3(CCCN3C(=O)C4=C(C=CC(=C4)OC)N5N=CC=N5)C)Cl")

# Should we add a seconf fine DFT filter?
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


# Instantiate the Promethium client and workflow parameters
prom = PromethiumClient()
cs_payload = CreateConformerSearchWorkflowRequest(**job_params)

# Estimate required GPU memory for workflow
cs_memory = prom.workflows.memory(cs_payload)
print(f"Estimated GPU memory usage: {cs_memory.prediction_bytes/BYTES_PER_GB} GB")
print(
    "Estimated GPU memory usage range: "
    f"({cs_memory.percentile_prediction_bytes['0.025']/BYTES_PER_GB}, "
    f"{cs_memory.percentile_prediction_bytes['0.975']/BYTES_PER_GB}) GB")

# Submit a CS workflow using the above configuration
cs_workflow = prom.workflows.submit(cs_payload)
print(f"Workflow {cs_workflow.name} submitted with id: {cs_workflow.id}")

# Wait for the workflow to finish
prom.workflows.wait(cs_workflow.id)

# Get the status and elapsed time
cs_workflow = prom.workflows.get(cs_workflow.id)
print(f"Workflow {cs_workflow.name} completed with status: {cs_workflow.status}")
print(f"Workflow completed in {cs_workflow.duration_seconds:.2f}s")

# Obtain the numeric results
cs_results = prom.workflows.results(cs_workflow.id)
with open(os.path.join(foldername, f"{cs_workflow.name}_results.json"), "w") as fp:
    fp.write(cs_results.model_dump_json(indent=2))

# Extract and print the conformers
conformers = cs_results.get_artifact("conformers")
print("Conformers:\n====================\n")
print(conformers)

# Download results
with open(os.path.join(foldername, f"{cs_workflow.name}_results.zip"), "wb") as fp:
    fp.write(prom.workflows.download(cs_workflow.id))

