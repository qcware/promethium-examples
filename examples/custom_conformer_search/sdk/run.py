import copy
import os

from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateConformerSearchWorkflowRequest,
)
from promethium_sdk.utils import (
    base64encode,
)

# Est. Runtimes:
# Wall-clock / Real-world time:
# Diethyl Ether = <10 mins
# Daridorexant = <15 mins
#
# Billable compute time:
# Diethyl Ether = <10 mins
# Daridorexant = ~3.5-4.0 hours

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)


job_params = {
    "name": "sdk-customer-conformer-search",
    "version": "v1",
    "kind": "ConformerSearch",
    "parameters": {
        "molecule": {},
        "params": {
            "confgen_max_n_conformers": 30,
            "confgen_rmsd_threshold": 0.3,
            "charge": 0,
            "multiplicity": 1,
        },
        "filters": [
            {
                "filtertype": "DFT",
                "params": {
                    "maxiter": 15,
                    "energy_threshold": 5,
                    "do_geometry_optimization": True,
                    "distance_threshold": 0.005,
                    "g_thresh": 1e-3
                },
                "system": {
                    "params": {
                        "basisname": "minix",
                        "jkfit_basisname": "def2-universal-jkfit",
                        "methodname": "hf-3c",
                        "xc_grid_scheme": "SG0",
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
                }
            },
            {
                "filtertype": "DFT",
                "params": {
                    "maxiter": 15,
                    "energy_threshold": 5,
                    "do_geometry_optimization": True,
                    "distance_threshold": 0.005,
                    "g_thresh": 1e-4
                },
                "system": {
                    "params": {
                        "basisname": "def2-svp",
                        "jkfit_basisname": "def2-universal-jkfit",
                        "methodname": "b3lyp-d3",
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
                }
            },
            {
                "filtertype": "DFT",
                "params": {
                    "maxiter": 100,
                    "energy_threshold": 5,
                    "do_geometry_optimization": False,
                    "distance_threshold": 0.005,
                    "g_thresh": 1e-4
                },
                "system": {
                    "params": {
                        "basisname": "def2-tzvp",
                        "jkfit_basisname": "def2-universal-jkfit",
                        "methodname": "wb97m-v",
                        "xc_grid_scheme": "SG2",
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
                }
            }
        ],
    },
    "resources": {"gpu_type": "a100"},
}


prom = PromethiumClient()

SMILES = [
    "CCOCC", #Diethyl Ether
    "CC1=C(C=CC2=C1N=C(N2)C3(CCCN3C(=O)C4=C(C=CC(=C4)OC)N5N=CC=N5)C)Cl", #Daridorexant
]

workflow_ids = []
for i, smile in enumerate(SMILES):
    tmp_job_params = copy.deepcopy(job_params)
    # Set the molecule:
    tmp_job_params["name"] = f"conformer-search-GS-{i}-Custom-A100"
    tmp_job_params["parameters"]["molecule"] = {
        "base64data": base64encode(smile),
        "filetype": "smi",
    }
    payload = CreateConformerSearchWorkflowRequest(**tmp_job_params)
    # Submit but don't wait:
    workflow = prom.workflows.submit(payload)
    workflow_ids.append(workflow.id)
    print(f"Workflow {workflow.name} submitted with id: {workflow.id}")

# Wait for all workflows to complete:
# Actually no need to do this here.
# It often makes sense to decouple the submission script from the results
# generation script. That way, the submission script can run,
# generate the workflow ids (store them), and then the results generation script
# can be run at a later time (and re-run if there are bugs).
# This is especially useful if you are running many workflows.
# However, for simplicity here, we wait in the same script.
for workflow_id in workflow_ids:
    prom.workflows.wait(workflow_id)

    workflow = prom.workflows.get(workflow_id)
    print(f"Workflow {workflow.name} completed with status: {workflow.status}")
    print(f"Workflow completed in {workflow.duration_seconds:.2f}s")

    cs_results = prom.workflows.results(workflow_id)
    with open(f"{foldername}/{workflow.name}_results.json", "w") as fp:
        fp.write(cs_results.model_dump_json(indent=2))

    # Get conformers:
    conformers = cs_results.get_artifact("conformers")
    print("Conformers:\n====================\n")
    print(conformers)
