import base64
import os

from promethium.client import PromethiumClient
from promethium.models import (
    CreateConformerSearchWorkflowRequest,
)
from promethium.utils import (
    base64encode,
)

# Note:
# Run times for some of these conformers searches is non-trivial ~1-1.5hrs wall time
# with slightly more than that in total GPU time.

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

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
                "key": "FF",
            },
            {
                "filtertype": "ANI",
                "params": {
                    "max_n_conformers": 25,
                    "energy_threshold": 10,
                    "distance_threshold": 0.005,
                    "do_geometry_optimization": True,
                },
                "key": "ANI",
            },
        ],
    },
    "resources": {"gpu_type": "v100"},
}


prom = PromethiumClient(api_key=os.environ["PM_API_KEY"])

SMILES = [
    "C1=CN=C(C=N1)C(=O)N",
    "CC(=O)NC1=C(C(=C(C(=C1I)C(=O)O)I)NC(=O)C)I",
    "CC(=O)OC1=CC=CC=C1C(=O)O",
    "CCC(=C)C(=O)C1=C(C(=C(C=C1)OCC(=O)O)Cl)Cl",
    "CN1C(=O)CN=C(C2=C1C=CC(=C2)[N+](=O)[O-])C3=CC=CC=C3F",
    "C(C(F)(F)F)(Cl)Br",
    "CCCC(C)(COC(=O)N)COC(=O)N",
    "CCCC(C)C1(C(=O)NC(=O)NC1=O)CC",
    "CCCC(C)C1(C(=O)NC(=O)NC1=O)CC=C",
    "C[N+](C)(C)CCOC(=O)CCC(=O)OCC[N+](C)(C)C",
]

workflow_ids = []
for i, smile in enumerate(SMILES):
    # Set the molecule:
    job_params["name"] = f"conformer-search-GS-{i}"
    job_params["parameters"]["molecule"] = {
        "base64data": base64encode(smile),
        "filetype": "smi",
    }
    payload = CreateConformerSearchWorkflowRequest(**job_params)
    # Submit but don't wait:
    workflow = prom.workflows.submit(payload)
    workflow_ids.append(workflow.id)
    print(f"Workflow {workflow.name} submitted with id: {workflow.id}")

# Wait for all workflows to complete:
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
