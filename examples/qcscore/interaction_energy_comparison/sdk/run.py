import copy
import os
import zipfile

from promethium_sdk.utils import base64decode, base64encode, KCAL_PER_MOL_PER_HARTREE
from promethium_sdk.client import PromethiumClient

from promethium_sdk.models import (
    CreateInteractionEnergyCalculationWorkflowRequest,
    PrepareCutoutRequest,
    ProjectKind,
    WorkflowStatus
)

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100-80gb")

if not os.path.exists(foldername):
    os.makedirs(foldername)

prom = PromethiumClient()

# Get the QCScore project workflow ID, and load the project settings.
qcscore_project_id = input("Enter QCScore project ID: ")
qcscore_project_id = qcscore_project_id.strip()
qcscore_project = prom.projects.get(qcscore_project_id)
if qcscore_project.kind.value != ProjectKind.QuantumChemicalScoring.value:
    print(f"ERROR: Project {qcscore_project.name} has unexpected kind {qcscore_project.kind}.")
    exit()

# Configure the Interaction Energy workflow by copying the QCScore project settings.
default_ie_job_params = {
    "version": "v1",
    "kind": "InteractionEnergyCalculation",
    "parameters": qcscore_project.properties.scoring.model_dump(exclude_none=True),
    "resources": { "gpu_type": gpu_type },
}
default_ie_job_params["parameters"]["molecule_a"] = {
    "filetype": "xyz",
    "params": { "multiplicity": 1 },
}
default_ie_job_params["parameters"]["molecule_b"] = {
    "filetype": "xyz",
    "params": { "multiplicity": 1 },
}

# Ensure that we set the multiplicity to 1.
if "hf" not in default_ie_job_params["parameters"].keys():
    default_ie_job_params["parameters"]["hf"] = {}
if "params" not in default_ie_job_params["parameters"]["hf"].keys():
    default_ie_job_params["parameters"]["hf"]["params"] = {}
default_ie_job_params["parameters"]["hf"]["params"]["multiplicity"] = 1

# Overwrite any other JK builders with a numerical JK builder to accommodate larger structures.
default_ie_job_params["parameters"]["jk_builder"] = {
    "type": "numerical_jk",
    "params": {
        "pme_cutoff": 1e-14,
        "pme_sr_cutoff": 1e-14,
        "pme_grid_spacing": 0.25,
    },
}

# Collect all the results from the QCScore project.
results_page = prom.projects.results(id=qcscore_project_id, page=1, size=10)
all_results = results_page.items
while (results_page.page * results_page.size) < results_page.total:
    results_page = prom.projects.results(
        id=qcscore_project_id,
        page=results_page.page + 1,
        size=results_page.size)
    all_results.extend(results_page.items)
print(f"Processing {len(all_results)} results for QCScore project '{qcscore_project.name}':")

# Build a map where the key is the Fragmented Interaction Energy (FIE) workflow ID,
# and the value contains a dictionary of values to identify the name and score,
# and the Interaction Energy workflow ID.
qcscore_results_by_fie_id = {}
for r in all_results:
    # Collect the FIE workflow information to populate the map.
    score = None
    if hasattr(r.results.root.results, "score"):
        score = r.results.root.results.score * KCAL_PER_MOL_PER_HARTREE
    qcscore_results_by_fie_id[r.target_resource_id] = {
        "name": r.name,
        "score": score,
    }
    if r.results.root.status != WorkflowStatus.COMPLETED:
        print(f"Skipping '{r.name}' (FIE workflow id={r.target_resource_id}) with status {r.results.root.status.value}.")
        continue
    if score is None:
        print(f"Skipping '{r.name}' (FIE workflow id={r.target_resource_id}) because score is missing.")
        continue

    # Download and unzip the FIE workflow results.
    results_foldername = os.path.join(foldername, f"{r.target_resource_id}_{r.name}")
    if not os.path.exists(results_foldername):
        os.makedirs(results_foldername)
    results_zipfile = os.path.join(results_foldername, "results.zip")
    with open(results_zipfile, "wb") as fp:
        fp.write(prom.workflows.download(r.target_resource_id))
    with zipfile.ZipFile(results_zipfile, "r") as zip_ref:
        zip_ref.extractall(results_foldername)

    # Read the optimized-subsystem.pdb from the FIE results.
    subsystem_pdb_filepath = os.path.join(results_foldername, "optimized-subsystem.pdb")
    if not os.path.exists(subsystem_pdb_filepath):
        print(f"Skipping '{r.name}' (FIE workflow id={r.target_resource_id}) because optimized-subsystem.pdb file is missing.")
        continue
    with open(subsystem_pdb_filepath, "r") as f:
        subsystem_pdb_contents = f.read()

    # Prepare a cutout to separate the ligand from the protein, and save the results.
    # We cutout with target_num_atoms high enough to collect all the protein atoms in the
    # subsystem, which must be less than the number of lines in the PDB file.
    cutout = prom.preparation.cutout(
        PrepareCutoutRequest(
            pdb_base64=base64encode(subsystem_pdb_contents),
            ligand_name="LIG",
            target_num_atoms=subsystem_pdb_contents.count('\n'),
            include_fragments=True,
            neutral_termini=False,
        )
    )
    with open(os.path.join(results_foldername, "optimized-subsystem-ligand.xyz"), "w") as fp:
        fp.write(base64decode(cutout.ligand_xyz_base64))
    with open(os.path.join(results_foldername, "optimized-subsystem-protein.xyz"), "w") as fp:
        fp.write(base64decode(cutout.protein_xyz_base64))

    # Start an Interaction Energy workflow with the protein and ligand.
    ie_job_params = copy.deepcopy(default_ie_job_params)
    ie_job_params["name"] = r.name
    ie_job_params["parameters"]["molecule_a"]["base64data"] = cutout.ligand_xyz_base64
    ie_job_params["parameters"]["molecule_a"]["params"]["charge"] = cutout.ligand_charge
    ie_job_params["parameters"]["molecule_b"]["base64data"] = cutout.protein_xyz_base64
    ie_job_params["parameters"]["molecule_b"]["params"]["charge"] = cutout.protein_charge
    ie_job_payload = CreateInteractionEnergyCalculationWorkflowRequest(**ie_job_params)
    ie_workflow = prom.workflows.submit(ie_job_payload)
    qcscore_results_by_fie_id[r.target_resource_id]["ie_workflow_id"] = ie_workflow.id
    print(f"Started Interaction Energy workflow '{r.name}' (IE workflow id={ie_workflow.id}).")

print()
print("Waiting for Interaction Energy workflows to complete...")
for key in qcscore_results_by_fie_id.keys():
    ie_workflow_id = qcscore_results_by_fie_id[key]["ie_workflow_id"]
    prom.workflows.wait(ie_workflow_id)
    ie_workflow = prom.workflows.get(ie_workflow_id)
    print(f"Interaction Energy workflow '{ie_workflow.name}' (id={ie_workflow.id}) completed in {ie_workflow.duration_seconds:.2f}s with status {ie_workflow.status.value}.")
    if ie_workflow.status == WorkflowStatus.COMPLETED:
        name = qcscore_results_by_fie_id[key]["name"]
        score = qcscore_results_by_fie_id[key]["score"]
        ie_results = prom.workflows.results(ie_workflow_id)
        interaction_energy = ie_results.results["interaction_energy"]["raw_interaction_energy"] * KCAL_PER_MOL_PER_HARTREE
        qcscore_results_by_fie_id[key]["interaction_energy"] = interaction_energy
        print(f"  {name}: Interaction Energy = {interaction_energy} kcal/mol, QCScore = {score} kcal/mol")

# Print a table of the scores compared with the interaction energies.
sorted_ligands = sorted(
    list(qcscore_results_by_fie_id.values()),
    key=lambda x: x["score"] if "score" in x.keys() else float("inf")
)
empty_energy_value = "             ---"
print()
print("                      ligand |            score |      int. energy ")
print("-----------------------------+------------------+------------------")
for ligand in sorted_ligands:
    name_str = f'{ligand["name"]:>28s}'
    score_str = f'{ligand["score"]:16.8f}' if "score" in ligand.keys() else empty_energy_value
    ie_str = f'{ligand["interaction_energy"]:16.8f}' if "interaction_energy" in ligand.keys() else empty_energy_value
    print(f"{name_str} | {score_str} | {ie_str}")
