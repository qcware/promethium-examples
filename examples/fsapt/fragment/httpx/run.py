import base64
import json
import httpx
import os
import pathlib

from promethium_sdk.utils import base64decode

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")

if not os.path.exists(foldername):
    os.makedirs(foldername)

headers = {
    "x-api-key": os.environ["PM_API_KEY"],
    "accept": "application/json",
    "content-type": "application/json",
}

client = httpx.Client(base_url=base_url, headers=headers)

pdb_file_path = os.path.join(pathlib.Path(__file__).parent.parent.resolve(), "6c1r_efd.pdb")
with open(pdb_file_path, "rb") as f:
    pdb_base64data = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "pdb_base64": pdb_base64data,
    "cutoff": 5.0,
    "full_residue": True,
    "keep_non_proteins": True,
    "ligand_name": "EFD",
    "include_fragments": True,
}
response = client.post("/v0/preparation/cutout", json=payload).json()

with open(os.path.join(foldername, "results.json"), "w") as fp:
    fp.write(json.dumps(response))
with open(os.path.join(foldername, "complex.xyz"), "w") as fp:
    fp.write(base64decode(response["complex_xyz_base64"]))
with open(os.path.join(foldername, "ligand.xyz"), "w") as fp:
    fp.write(base64decode(response["ligand_xyz_base64"]))
with open(os.path.join(foldername, "ligand.pdb"), "w") as fp:
    fp.write(base64decode(response["ligand_pdb_base64"]))
with open(os.path.join(foldername, "protein.xyz"), "w") as fp:
    fp.write(base64decode(response["protein_xyz_base64"]))
with open(os.path.join(foldername, "protein.pdb"), "w") as fp:
    fp.write(base64decode(response["protein_pdb_base64"]))

print(f"Ligand charge: {response['ligand_charge']}")
if response.get("ligand_charge_warning_info"):
    print(f"    * NOTE: {response['ligand_charge_warning_info']}")

print(f"Protein charge: {response['protein_charge']}")
for residue_name, residue_details in response['protein_charge_detail'].items():
    print(f"    {residue_name}: charge={residue_details['charge']}, count={residue_details['count']}")

print("Fragments:")
for fragment_name, fragment in zip(response["fragment_names"], response["fragments"]):
    print(f"    {fragment_name}: {fragment}")
print(f"Included residues: {response['included_residues']}")
