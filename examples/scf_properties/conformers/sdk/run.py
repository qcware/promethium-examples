import os
import zipfile

from promethium_sdk.utils import base64encode
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    # This requires an SDK version >= 0.3.12 for the SCF properties.
    CreateSinglePointCalculationWorkflowRequest,
    WorkflowStatus,
    WorkflowKind,
)

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

prom = PromethiumClient()

# Get the conformer search workflow and ensure that it succeeded.
cs_workflow_id = input("Enter Conformer Search workflow ID: ")
cs_workflow_id = cs_workflow_id.strip()

cs_workflow = prom.workflows.get(cs_workflow_id)
if cs_workflow.kind != WorkflowKind.ConformerSearch:
    print(f"ERROR: Workflow {cs_workflow.name} has unexpected kind {cs_workflow.kind}.")
    exit()

if cs_workflow.status == WorkflowStatus.RUNNING:
    print(f"Waiting for workflow {cs_workflow.name} to complete...")
    prom.workflows.wait(cs_workflow_id)
    cs_workflow = prom.workflows.get(cs_workflow_id)

if cs_workflow.status != WorkflowStatus.COMPLETED:
    print(f"ERROR: Workflow {cs_workflow.name} completed with status {cs_workflow.status}.")
    exit()
print(f"Workflow {cs_workflow.name} completed with status {cs_workflow.status} in {cs_workflow.duration_seconds:.2f}s")

# Save the conformer search results.
cs_workflow_results = prom.workflows.results(cs_workflow.id)
with open(os.path.join(foldername, f"{cs_workflow.name}_results.json"), "w") as fp:
    fp.write(cs_workflow_results.model_dump_json(indent=2))
cs_results_zipfile_path = os.path.join(foldername, f"{cs_workflow.name}_results.zip")
with open(cs_results_zipfile_path, "wb") as fp:
    fp.write(prom.workflows.download(cs_workflow.id))

# Collect the resulting conformers and start SinglePointCalculation workflows to get the SCF properties.
spc_workflow_ids = []
with zipfile.ZipFile(cs_results_zipfile_path, "r") as zip_ref:
    for rank, conformer_index in enumerate(cs_workflow_results.results["indices"]):
        with zip_ref.open(f"conformer-{rank}.xyz") as f:
            mol_name = f"C{conformer_index}"
            mol_base64data = base64encode(f.read())

        job_params = {
            "name": f"spc_{cs_workflow.name}_{mol_name}",
            "version": "v1",
            "kind": "SinglePointCalculation",
            "parameters": {
                "molecule": {"base64data": mol_base64data, "filetype": "xyz"},
                "system": {
                    "params": {
                        "basisname": "def2-svp",
                        "methodname": "b3lyp",
                        "xc_grid_scheme": "SG2",
                    }
                },
                "hf": {
                    "params": {"charge": 0, "multiplicity": 1, "g_convergence": 0.000001},
                },
                "scf_properties": {
                    "outputs": [
                        {"type": "multipole_moments", "expansion_order": "2"},
                        {"type": "orbital_energies", "occupied_count": 5, "unoccupied_count": 5},
                        {"type": "polar_surface_area"},
                    ],
                },
            },
            "resources": {"gpu_type": gpu_type},
        }
        payload = CreateSinglePointCalculationWorkflowRequest(**job_params)
        spc_workflow = prom.workflows.submit(payload)
        print(f"Workflow {job_params.get('name')} submitted (id: {spc_workflow.id})")
        spc_workflow_ids.append(spc_workflow.id)

# Wait for all workflows to complete and get results.
conformer_scf_properties = []
for spc_workflow_id in spc_workflow_ids:
    prom.workflows.wait(spc_workflow_id)

    spc_workflow = prom.workflows.get(spc_workflow_id)
    print(f"Workflow {spc_workflow.name} completed with status {spc_workflow.status} in {spc_workflow.duration_seconds:.2f}s")

    spc_workflow_results = prom.workflows.results(spc_workflow.id)
    with open(os.path.join(foldername, f"{spc_workflow.name}_results.json"), "w") as fp:
        fp.write(spc_workflow_results.model_dump_json(indent=2))

    conformer_scf_properties.append(spc_workflow_results.results["scf_properties"])

    with open(os.path.join(foldername, f"{spc_workflow.name}_results.zip"), "wb") as fp:
        fp.write(prom.workflows.download(spc_workflow.id))

# Print a table of the SCF properties for each conformer.
conformer_names = [f"C{k}" for k in cs_workflow_results.results["indices"]]
conformer_ranks = [(k+1) for k in range(len(conformer_names))]
conformer_abs_energies = [cs_workflow_results.results[f"conformer_{k}_energy"][-1] for k in cs_workflow_results.results["indices"]]
print()
print("            |" + " |".join([f"{k:>16s}" for k in conformer_names]))
print("------------+" + "+".join(["-----------------" for k in conformer_names]))
print("       Rank |" + " |".join([f"{v:16.0f}" for v in conformer_ranks]))
print("     Weight |" + " |".join([f"{v:16.6f}" for v in cs_workflow_results.results["weights"]]))
print(" Rel Energy |" + " |".join([f"{v:16.6f}" for v in cs_workflow_results.results["energies"]]))
print("     Energy |" + " |".join([f"{v:16.6f}" for v in conformer_abs_energies]))
print("------------+" + "+".join(["-----------------" for k in conformer_names]))


# Print the polar surface area.
psa_values = [scf_props["polar_surface_area"] for scf_props in conformer_scf_properties]
print("        PSA |" + " |".join([f"{v:16.8f}" for v in psa_values]))

# Print orbital energy properties.
homo_values = [scf_props["orbital_energies"]["homo_index"] for scf_props in conformer_scf_properties]
print("       HOMO |" + " |".join([f"{v:16.0f}" for v in homo_values]))
lumo_values = [scf_props["orbital_energies"]["lumo_index"] for scf_props in conformer_scf_properties]
print("       LUMO |" + " |".join([f"{v:16.0f}" for v in lumo_values]))
alpha_homo = [scf_props["orbital_energies"]["alpha_homo_energy"] for scf_props in conformer_scf_properties]
print("     α HOMO |" + " |".join([f"{v:16.8f}" for v in alpha_homo]))
alpha_lumo = [scf_props["orbital_energies"]["alpha_lumo_energy"] for scf_props in conformer_scf_properties]
print("     α LUMO |" + " |".join([f"{v:16.8f}" for v in alpha_lumo]))
beta_homo = [scf_props["orbital_energies"]["beta_homo_energy"] for scf_props in conformer_scf_properties]
print("     β HOMO |" + " |".join([f"{v:16.8f}" for v in beta_homo]))
beta_lumo = [scf_props["orbital_energies"]["beta_lumo_energy"] for scf_props in conformer_scf_properties]
print("     β LUMO |" + " |".join([f"{v:16.8f}" for v in beta_lumo]))

# Print dipole and quadrupole moments.
multipole_moments = [scf_props["multipole_moments"][0]["multipole_moments"] for scf_props in conformer_scf_properties]
for vals in zip(*multipole_moments):
    label = vals[0]["component_label"]
    print(f"{label:>11s} |" + " |".join([f"{v['value']:16.8f}" for v in vals]))
