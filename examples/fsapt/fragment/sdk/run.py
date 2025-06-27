import os
import pathlib

from promethium_sdk.utils import (
    base64decode,
    base64encode,
)
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    PrepareCutoutRequest,
)

foldername = "output"
if not os.path.exists(foldername):
    os.makedirs(foldername)

prom = PromethiumClient()

pdb_file_path = os.path.join(pathlib.Path(__file__).parent.parent.resolve(), "6c1r_efd.pdb")
with open(pdb_file_path, "r") as f:
    pdb_base64data = base64encode(f.read())

prepare_cutout_request = PrepareCutoutRequest(
    pdb_base64=pdb_base64data,
    cutoff=5.0,
    full_residue=True,
    keep_non_proteins=True,
    ligand_name="EFD",
    include_fragments=True,
)
response = prom.preparation.cutout(prepare_cutout_request)

with open(os.path.join(foldername, "results.json"), "w") as fp:
    fp.write(response.model_dump_json(indent=2))
with open(os.path.join(foldername, "complex.xyz"), "w") as fp:
    fp.write(base64decode(response.complex_xyz_base64))
with open(os.path.join(foldername, "ligand.xyz"), "w") as fp:
    fp.write(base64decode(response.ligand_xyz_base64))
with open(os.path.join(foldername, "ligand.pdb"), "w") as fp:
    fp.write(base64decode(response.ligand_pdb_base64))
with open(os.path.join(foldername, "protein.xyz"), "w") as fp:
    fp.write(base64decode(response.protein_xyz_base64))
with open(os.path.join(foldername, "protein.pdb"), "w") as fp:
    fp.write(base64decode(response.protein_pdb_base64))

print(f"Ligand charge: {response.ligand_charge}")
if response.ligand_charge_warning_info:
    print(f"    * NOTE: {response.ligand_charge_warning_info}")

print(f"Protein charge: {response.protein_charge}")
for residue_name, residue_details in response.protein_charge_detail.items():
    print(f"    {residue_name}: charge={residue_details['charge']}, count={residue_details['count']}")

print("Fragments:")
for fragment_name, fragment in zip(response.fragment_names, response.fragments):
    print(f"    {fragment_name}: {fragment}")
print(f"Included residues: {response.included_residues}")
