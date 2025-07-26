import os

from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateInteractionEnergyCalculationWorkflowRequest,
)

# This requires an SDK version >= 0.4.7 for the conversion constant.
from promethium_sdk.utils import base64encode, KCAL_PER_MOL_PER_HARTREE

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

moleculeA_adenine = base64encode(
"""15

N 0.2793014000 2.4068393000 -0.6057517000
C -1.0848570000 2.4457461000 -0.5511608000
H -1.6594403000 3.0230294000 -1.2560905000
N -1.5977117000 1.7179877000 0.4287543000
C -0.4897255000 1.1714358000 1.0301910000
C -0.3461366000 0.2914710000 2.1172343000
N -1.4187090000 -0.1677767000 2.8101441000
H -1.2388750000 -0.9594802000 3.4047578000
H -2.2918734000 -0.1788223000 2.3073619000
N 0.8857630000 -0.0700763000 2.4919494000
C 1.9352348000 0.4072878000 1.7968022000
H 2.9060330000 0.0788414000 2.1458181000
N 1.9409775000 1.2242019000 0.7402202000
C 0.6952186000 1.5779858000 0.4063984000
H 0.8610073000 2.8298045000 -1.3104502000
"""
)

moleculeB_thymine = base64encode(
"""15

N 1.2754606000 -0.6478993000 -1.9779104000
C 1.4130533000 -1.5536850000 -0.9550667000
H 2.4258769000 -1.8670780000 -0.7468778000
C 0.3575976000 -2.0239499000 -0.2530575000
C 0.4821292000 -3.0179494000 0.8521221000
H 0.1757705000 -2.5756065000 1.7986281000
H -0.1601691000 -3.8770412000 0.6639498000
H 1.5112443000 -3.3572767000 0.9513659000
C -0.9684711000 -1.5298112000 -0.5939792000
O -2.0029280000 -1.8396957000 -0.0199453000
N -0.9956916000 -0.6383870000 -1.6720420000
H -1.9014057000 -0.2501720000 -1.8985760000
C 0.0684702000 -0.1191762000 -2.3763759000
O -0.0397875000 0.7227006000 -3.2531083000
H 2.0853289000 -0.2760176000 -2.4454577000
"""
)

ie_name = "adenine-thymine-stacked-complex-wB97M-V_def2-TZVP"
job_params = {
    "name": ie_name,
    "version": "v1",
    "kind": "InteractionEnergyCalculation",
    "parameters": {
        "molecule_a": {
            "base64data": moleculeA_adenine,
            "filetype": "xyz",
            "params": {
                "charge": 0,
                "multiplicity": 1,
            },
        },
        "molecule_b": {
            "base64data": moleculeB_thymine,
            "filetype": "xyz",
            "params": {
                "charge": 0,
                "multiplicity": 1,
            },
        },
        "interaction_energy": {
            "params": {
                "print_level": 0,
                "cluster_multiplicity": 1,
            },
        },
        "system": {
            "params": {
                "basisname": "def2-tzvp",
                "methodname": "wb97m-v",
                "xc_grid_scheme": "SG2",
            },
        },
        "hf": {
            "params": {
                "charge": 0,
                "multiplicity": 1,
                "g_convergence": 0.000001,
            },
            "outputs": {
                "gradient": False,
                "polarizability": False,
                "dipole_derivative": False,
            },
        },
        "est": {
            "params": {},
        },
        "jk_builder": {
            "type": "core_dfjk",
            "params": {},
        },
        "xc_builder": {
            "params": {},
        },
    },
    "resources": {
        "gpu_type": gpu_type,
    },
}

prom = PromethiumClient()
payload = CreateInteractionEnergyCalculationWorkflowRequest(**job_params)
print(f"Submitting {ie_name}...")
workflow = prom.workflows.submit(payload)

prom.workflows.wait(workflow.id)

workflow = prom.workflows.get(workflow.id)
print(f"Workflow {workflow.name} completed with status: {workflow.status}")
print(f"Workflow completed in {workflow.duration_seconds:.2f}s")

ie_results = prom.workflows.results(workflow.id)
with open(f"{foldername}/{workflow.name}_results.json", "w") as fp:
    fp.write(ie_results.model_dump_json(indent=2))

# Numeric results:
interaction_energy = KCAL_PER_MOL_PER_HARTREE * ie_results.results["interaction_energy"]["raw_interaction_energy"]
cp_corrected_interaction_energy = KCAL_PER_MOL_PER_HARTREE * ie_results.results["interaction_energy"]["cp_corrected_interaction_energy"]
basis_set_superposition_error = KCAL_PER_MOL_PER_HARTREE * ie_results.results["interaction_energy"]["basis_set_superposition_error"]
print(f"Interaction Energy:               {interaction_energy}")
print(f"CP-Corrected Interaction Energy:  {cp_corrected_interaction_energy}")
print(f"Basis Set Superposition Error:    {basis_set_superposition_error}")

# Download:
with open(os.path.join(foldername, f"{workflow.name}_results.zip"), "wb") as fp:
    fp.write(prom.workflows.download(workflow.id))
