import base64
import json
import httpx
import os
import pathlib

from promethium_sdk.utils import wait_for_workflows_to_complete

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

headers = {
    "x-api-key": os.environ["PM_API_KEY"],
    "accept": "application/json",
    "content-type": "application/json",
}

molecule_workflow_ids = {}
client = httpx.Client(base_url=base_url, headers=headers)

# Find XYZ files in the parent directory and use the file name to identify the molecule.
molecules_dir = pathlib.Path(__file__).parent.parent.resolve()
for file in os.listdir(molecules_dir):
    if not file.endswith(".xyz"):
        continue

    with open(os.path.join(molecules_dir, file), "rb") as f:
        mol_name = file.rsplit('.', 1)[0]
        mol_base64data = base64.b64encode(f.read()).decode("utf-8")

    # Create the SPC workflow with the molecule.
    job_params = {
        "name": f"spc_{mol_name}",
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

    # add metadata only if environment variables exist
    metadata = {}
    workflow_timeout = os.getenv("PM_WORKFLOW_TIMEOUT")
    task_timeout = os.getenv("PM_TASK_TIMEOUT")

    if workflow_timeout:
        metadata["workflow_timeout"] = int(workflow_timeout)
    if task_timeout:
        metadata["task_timeout"] = int(task_timeout)
    if metadata:
        job_params["metadata"] = metadata

    # submit a SPC workflow using the above configuration
    payload = job_params
    jobname = payload["name"]
    response = client.post("/v0/workflows", json=payload)
    with open(f"{foldername}/{jobname}_submitted.json", "w") as fp:
        fp.write(json.dumps(response.json()))
    workflow_id = response.json()["id"]
    print(f"Workflow {jobname} submitted with id: {workflow_id}")
    molecule_workflow_ids[mol_name] = workflow_id

# Wait for all workflows to complete and get results.
molecule_names = []
molecule_scf_properties = []
for mol_workflow_id in molecule_workflow_ids.items():
    mol_name = mol_workflow_id[0]
    workflow_id = mol_workflow_id[1]

    workflow = wait_for_workflows_to_complete(
        client=client,
        workflow_ids=[workflow_id],
        log_events=["STATE_CHANGES"],
        timeout=3600,
    )[workflow_id]

    # Get the status and Wall-clock time:
    response = client.get(f"v0/workflows/{workflow_id}").json()
    with open(f"{foldername}/{jobname}_status.json", "w") as fp:
        fp.write(json.dumps(response))
    name = response["name"]
    timetaken = response["duration_seconds"]
    print(f"Workflow {jobname} completed with status: {workflow['status']} in {timetaken:.2f}s")

    # Download results:
    response = client.get(
        f"/v0/workflows/{workflow_id}/results/download", follow_redirects=True
    )
    with open(f"{foldername}/{jobname}_results.zip", "wb") as fp:
        fp.write(response.content)

    # Extract and collect the SCF properties contained in the numeric results:
    response = client.get(f"/v0/workflows/{workflow_id}/results").json()
    with open(f"{foldername}/{jobname}_results.json", "w") as fp:
        fp.write(json.dumps(response))

    molecule_names.append(mol_name)
    molecule_scf_properties.append(response["results"]["scf_properties"])

# Print a table of the SCF properties for each molecule.
print()
print("        |" + " |".join([f"{k:>16s}" for k in molecule_names]))
print("--------+" + "+".join(["-----------------" for k in molecule_names]))

# Print the polar surface area.
psa_values = [scf_props["polar_surface_area"] for scf_props in molecule_scf_properties]
print("    PSA |" + " |".join([f"{v:16.8f}" for v in psa_values]))

# Print orbital energy properties.
homo_values = [scf_props["orbital_energies"]["homo_index"] for scf_props in molecule_scf_properties]
print("   HOMO |" + " |".join([f"{v:16.0f}" for v in homo_values]))
lumo_values = [scf_props["orbital_energies"]["lumo_index"] for scf_props in molecule_scf_properties]
print("   LUMO |" + " |".join([f"{v:16.0f}" for v in lumo_values]))
alpha_homo = [scf_props["orbital_energies"]["alpha_homo_energy"] for scf_props in molecule_scf_properties]
print(" α HOMO |" + " |".join([f"{v:16.8f}" for v in alpha_homo]))
alpha_lumo = [scf_props["orbital_energies"]["alpha_lumo_energy"] for scf_props in molecule_scf_properties]
print(" α LUMO |" + " |".join([f"{v:16.8f}" for v in alpha_lumo]))
beta_homo = [scf_props["orbital_energies"]["beta_homo_energy"] for scf_props in molecule_scf_properties]
print(" β HOMO |" + " |".join([f"{v:16.8f}" for v in beta_homo]))
beta_lumo = [scf_props["orbital_energies"]["beta_lumo_energy"] for scf_props in molecule_scf_properties]
print(" β LUMO |" + " |".join([f"{v:16.8f}" for v in beta_lumo]))

# Print dipole and quadrupole moments.
multipole_moments = [scf_props["multipole_moments"][0]["multipole_moments"] for scf_props in molecule_scf_properties]
for vals in zip(*multipole_moments):
    label = vals[0]["component_label"]
    print(f"{label:>7s} |" + " |".join([f"{v['value']:16.8f}" for v in vals]))

# This script will print a table which looks like this:
"""
        |     nordiazepam |      oxprenolol |       aprenolol |   ciprofloxacin |        mannitol
--------+-----------------+-----------------+-----------------+-----------------+-----------------
    PSA |    183.93120582 |    227.07657894 |    189.89728427 |    414.18630916 |    349.46907917
   HOMO |              69 |              71 |              67 |              86 |              48
   LUMO |              70 |              72 |              68 |              87 |              49
 α HOMO |     -0.24172379 |     -0.20047823 |     -0.21466671 |     -0.21562971 |     -0.25501103
 α LUMO |     -0.06942820 |     -0.00233016 |     -0.00329949 |     -0.05139053 |      0.01227417
 β HOMO |     -0.24172379 |     -0.20047823 |     -0.21466671 |     -0.21562971 |     -0.25501103
 β LUMO |     -0.06942820 |     -0.00233016 |     -0.00329949 |     -0.05139053 |      0.01227417
 charge |      0.00000000 |      0.00000000 |     -0.00000000 |      0.00000000 |      0.00000000
      X |     -0.38642679 |     -0.72746285 |      1.48432055 |     -2.03173614 |     -0.44395588
      Y |     -1.19912273 |      0.53754047 |      0.04209559 |     -2.43388235 |     -0.87329205
      Z |     -0.10955945 |      0.03153741 |     -0.27164320 |     -0.02257027 |     -0.64452434
     XX |    -75.63562881 |    -75.05099029 |    -74.74045661 |   -100.66200090 |    -68.06164760
     XY |     -1.20583735 |      2.68414576 |     -3.40404768 |     -3.13258230 |     -1.29494017
     XZ |      3.52699666 |      6.67335727 |     -4.71424280 |     -1.46260232 |      4.01094697
     YY |   -101.09801289 |    -81.36147870 |    -81.35629286 |   -103.12842528 |    -55.59342333
     YZ |      5.83067786 |     -0.91367550 |     -1.28195674 |     -2.50110991 |     -2.86690764
     ZZ |    -83.89617019 |    -85.69031435 |    -80.53181042 |   -103.51377362 |    -46.76234090
"""
