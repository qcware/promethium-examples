import base64
import json
import httpx
import os

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

client = httpx.Client(base_url=base_url, headers=headers)

input_mol = base64.b64encode(
    b"""9

    O   -1.510407226976    0.757898746844    0.000000000000
    O   -0.553334234073   -1.306832947272    0.000000000000
    C    0.851836372408    0.670262334922    0.000000000000
    C   -0.435392872548   -0.091344744168    0.000000000000
    C    2.037631538003    0.030293859895    0.000000000000
    H    0.778714996763    1.768162197756    0.000000000000
    H    2.070317763114   -1.070327443612    0.000000000000
    H    2.990077611988    0.580280001156    0.000000000000
    H   -2.306286818048    0.180092981979    0.000000000000"""
)

input_mol = input_mol.decode("utf-8")

job_params = {
    "name": "spc_atomic_charges",
    "version": "v1",
    "kind": "SinglePointCalculation",
    "parameters": {
        "molecule": {"base64data": input_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": "def2-svp",
                "methodname": "hf",
                "xc_grid_scheme": "SG2",
            }
        },
        "hf": {
            "params": {"charge": 0, "multiplicity": 1, "g_convergence": 0.000001},
        },
        "scf_properties": {
            "outputs": [
                {"type": "atomic_charges", "analysis_method": "mulliken"},
                {"type": "atomic_charges", "analysis_method": "lowdin"},
                {"type": "atomic_charges", "analysis_method": "iao"},
                {"type": "atomic_charges", "analysis_method": "resp"},
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
with open(os.path.join(foldername, f"{jobname}_submitted.json"), "w") as fp:
    fp.write(json.dumps(response.json()))
workflow_id = response.json()["id"]
print(f"Workflow {jobname} submitted with id: {workflow_id}")

# Wait for the workflow to finish
workflow = wait_for_workflows_to_complete(
    client=client,
    workflow_ids=[workflow_id],
    log_events=["STATE_CHANGES"],
    timeout=3600,
)[workflow_id]

# Get the status and Wall-clock time:
response = client.get(f"v0/workflows/{workflow_id}").json()
with open(os.path.join(foldername, f"{jobname}_status.json"), "w") as fp:
    fp.write(json.dumps(response))
name = response["name"]
timetaken = response["duration_seconds"]
print(f"Workflow {jobname} completed with status: {workflow['status']}")
print(f"Workflow completed in {timetaken:.2f}s")

# Download results:
response = client.get(
    f"/v0/workflows/{workflow_id}/results/download", follow_redirects=True
)
with open(os.path.join(foldername, f"{jobname}_results.zip"), "wb") as fp:
    fp.write(response.content)

# Extract and print the atomic charges contained in the numeric results:
response = client.get(f"/v0/workflows/{workflow_id}/results").json()
with open(os.path.join(foldername, f"{jobname}_results.json"), "w") as fp:
    fp.write(json.dumps(response))
atomic_charges = response["results"]["scf_properties"]["atomic_charges"]
atomic_charge_analysis_methods = [data["analysis_method"] for data in atomic_charges]
atomic_charge_analysis_results = [data["atomic_charges"] for data in atomic_charges]

print()
print(" Atom |" + " |".join([f"{k:>12s}" for k in atomic_charge_analysis_methods]))
print("------+" + "+".join(["-------------" for k in atomic_charge_analysis_methods]))
for n, vals in enumerate(zip(*atomic_charge_analysis_results)):
    print(f"  {n:3d} |" + " |".join([f"{v:12.8f}" for v in vals]))

# This script will print a table which looks like this (with minor numerical differences):
"""
 Atom |    mulliken |      lowdin |         iao |        resp
------+-------------+-------------+-------------+-------------
    0 | -0.37437257 | -0.12756925 | -0.53481521 | -0.65778992
    1 | -0.41297900 | -0.28500846 | -0.54429049 | -0.61056609
    2 | -0.23633031 | -0.09817325 | -0.20831543 | -0.29427909
    3 |  0.51611239 |  0.22104588 |  0.63909487 |  0.84930926
    4 |  0.01203033 |  0.05216236 | -0.18156946 | -0.30860144
    5 |  0.08354477 |  0.03970350 |  0.14808050 |  0.18337875
    6 |  0.10109182 |  0.04459825 |  0.15936747 |  0.20354619
    7 |  0.08306289 |  0.03691336 |  0.14638526 |  0.19056022
    8 |  0.22783968 |  0.11632762 |  0.37606249 |  0.44444211
"""

# For each analysis method, extract the bond orders as a dictionary of atom-pair to value, then print:
all_atom_pairs = set()
bond_order_analysis_methods = []
bond_order_analysis_results = []
for data in atomic_charges:
    if "bond_orders" not in data.keys():
        continue
    bond_orders_dict = {}
    for bond_order in data["bond_orders"]:
        atom_pair = f"{bond_order['atom_index_1']}-{bond_order['atom_index_2']}"
        bond_orders_dict[atom_pair] = bond_order["bond_order"]
    bond_order_analysis_methods.append(data["analysis_method"])
    bond_order_analysis_results.append(bond_orders_dict)
    all_atom_pairs.update(bond_orders_dict.keys())

print()
print(" Atom Pair |" + " |".join([f"{k:>12s}" for k in bond_order_analysis_methods]))
print("-----------+" + "+".join(["-------------" for k in bond_order_analysis_methods]))
for atom_pair in sorted(all_atom_pairs):
    vals = [results_dict.get(atom_pair, None) for results_dict in bond_order_analysis_results]
    print(f"  {atom_pair:>8s} |" + " |".join([f"{v:12.8f}" if v else "         n/a" for v in vals]))

# This script will print a table which looks like this (with minor numerical differences):
"""
 Atom Pair |    mulliken |      lowdin |         iao
-----------+-------------+-------------+-------------
       0-3 |  1.10807535 |  1.30713248 |  1.04301373
       0-8 |  0.94120572 |  1.07689118 |  0.83399933
       1-3 |  1.98675574 |  2.18700234 |  1.74322101
       2-3 |  0.98348079 |  1.06766134 |  1.00427294
       2-4 |  1.94482375 |  1.96587240 |  1.93232799
       2-5 |  0.97117201 |  0.93897566 |  0.94913670
       3-0 |  1.10807535 |  1.30713248 |  1.04301373
       3-1 |  1.98675574 |  2.18700234 |  1.74322101
       3-2 |  0.98348079 |  1.06766134 |  1.00427294
       4-2 |  1.94482375 |  1.96587240 |  1.93232799
       4-6 |  0.96456055 |  0.95583015 |  0.95177423
       4-7 |  0.97388370 |  0.96123140 |  0.96127085
       5-2 |  0.97117201 |  0.93897566 |  0.94913670
       6-4 |  0.96456055 |  0.95583015 |  0.95177423
       7-4 |  0.97388370 |  0.96123140 |  0.96127085
       8-0 |  0.94120572 |  1.07689118 |  0.83399933
"""
