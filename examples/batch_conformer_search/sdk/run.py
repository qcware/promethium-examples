import copy
import os

from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateConformerSearchWorkflowRequest,
)
from promethium_sdk.utils import (
    base64encode,
)

# Note:
# Run times for some of these conformers searches is non-trivial ~1-1.5hrs wall time
# with slightly more than that in total GPU time.

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

# Should we add a coarse DFT filter?
coarse_dft = True

if not os.path.exists(foldername):
    os.makedirs(foldername)


job_params = {
    "name": "sdk-conformer-search",
    "version": "v1",
    "kind": "ConformerSearch",
    "parameters": {
        "molecule": {},
        "params": {
            "confgen_max_n_conformers": 250,
            "confgen_rmsd_threshold": 0.3,
            "charge": 0,
            "multiplicity": 1,
        },
        "filters": [
            {
                "filtertype": "ForceField",
                "params": {
                    "do_geometry_optimization": True,
                    "forcefield_type": "MMFF",
                    "max_n_conformers": 150,
                    "energy_threshold": 15,
                    "rmsd_threshold": 0.3,
                    "coulomb_distance_threshold": 0.005,
                },
            },
            {
                "filtertype": "ANI",
                "params": {
                    "max_n_conformers": 25,
                    "energy_threshold": 10,
                    "distance_threshold": 0.005,
                    "do_geometry_optimization": True,
                },
            },
        ],
    },
    "resources": {"gpu_type": gpu_type},
}

# Optional coarse DFT filter:
coarse_dft_filter = {
    "filtertype": "DFT",
    "params": {
        "maxiter": 15,
        "energy_threshold": 5,
        "do_geometry_optimization": True,
        "distance_threshold": 0.005
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
    },
}

prom = PromethiumClient()

SMILES = [
    "C1=CN=C(C=N1)C(=O)N",
    "CC(=O)OC1=CC=CC=C1C(=O)O",
    "CCC(=C)C(=O)C1=C(C(=C(C=C1)OCC(=O)O)Cl)Cl",
    "CN1C(=O)CN=C(C2=C1C=CC(=C2)[N+](=O)[O-])C3=CC=CC=C3F",
    "CCCC(C)(COC(=O)N)COC(=O)N",
    "CCCC(C)C1(C(=O)NC(=O)NC1=O)CC",
    "CCCC(C)C1(C(=O)NC(=O)NC1=O)CC=C",
]

workflow_ids = []
for i, smile in enumerate(SMILES):
    tmp_job_params = copy.deepcopy(job_params)
    # Set the molecule:
    tmp_job_params["name"] = f"conformer-search-GS-{i}{'-DFT' if coarse_dft else ''}"
    tmp_job_params["parameters"]["molecule"] = {
        "base64data": base64encode(smile),
        "filetype": "smi",
    }
    # Optionally add the coarse DFT filter:
    if coarse_dft:
        tmp_job_params["parameters"]["filters"].append(coarse_dft_filter)
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
    with open(os.path.join(foldername, f"{workflow.name}_results.json"), "w") as fp:
        fp.write(cs_results.model_dump_json(indent=2))

    # Get conformers:
    conformers = cs_results.get_artifact("conformers")
    print("Conformers:\n====================\n")
    print(conformers)
