import json
import os
import pathlib

from promethium_sdk.utils import base64encode, KCAL_PER_MOL_PER_HARTREE
from promethium_sdk.client import PromethiumClient

# This requires an SDK version >= 0.4.7 for QCScore projects support.
from promethium_sdk.models import (
    CreateFragmentedInteractionEnergyRequest,
    CreateQuantumChemicalScoringProjectRequest,
    CreateWorkflowRequestUnion,
    FragmentedInteractionEnergyInputSpec,
    MoleculeChargesRequest,
    MoleculeInput,
    MoleculeInputWithChargeAndMultiplicity,
    MoleculeToPdbRequest,
    PrepareCutoutRequest,
    ProjectResourceKind,
    QuantumChemicalScoringProjectProperties,
    ResourceRequest,
    WorkflowKind,
)

gpu_type = os.getenv("PM_GPU_TYPE", "a100-80gb")


def extract_ligand_name(ligand_sdf: str) -> str:
    """
    Extract the ligand name from the ligand SDF string. The convention for
    an SDF format is that the first line is the name.
    """
    ligand_sdf_lines = ligand_sdf.lstrip().split("\n")
    ligand_name = ligand_sdf_lines[0].strip()
    if len(ligand_name) == 0:
        raise ValueError(f"Could not determine ligand name from SDF contents: {ligand_sdf_lines[0]}")
    return ligand_name


prom = PromethiumClient()

# Find the protein and ligand files in the parent directory.
molecules_dir = pathlib.Path(__file__).parent.parent.resolve()
with open(os.path.join(molecules_dir, "t4lysozyme_uvt_protein.pdb"), "r") as f:
    protein_base64data = base64encode(f.read())

# The ligand file is a multi-SDF, which we can split into separate files.
with open(os.path.join(molecules_dir, "t4lysozyme_uvt_ligands.sdf"), "r") as f:
    full_ligands_text = f.read()

ligand_sdf_texts = [
    ligand.lstrip()
    for ligand in full_ligands_text.split("$$$$")
    if ligand.lstrip() != ""
]

# Infer the charges for each ligand.
ligand_charges_response = prom.molecule.charges(
    MoleculeChargesRequest(
        molecules=[
            MoleculeInput(
                base64data=base64encode(ligand_sdf_text),
                filetype="sdf",
            )
            for ligand_sdf_text in ligand_sdf_texts
        ]
    )
)
ligand_charges = [x.inferred_charge for x in ligand_charges_response.molecule_charges]

# Build a map of the ligand name to the corresponding molecule input.
ligand_name_to_molecule_input = {}
for sdf_text, charge in zip(ligand_sdf_texts, ligand_charges):
    ligand_name = extract_ligand_name(ligand_sdf=sdf_text)
    if ligand_name in ligand_name_to_molecule_input.keys():
        raise KeyError(f"Duplicate ligand name: {ligand_name}")
    if charge is None:
        raise ValueError(f"Failed to infer charges for ligand: {ligand_name}")
    ligand_name_to_molecule_input[ligand_name] = MoleculeInputWithChargeAndMultiplicity(
        base64data=base64encode(sdf_text),
        filetype="sdf",
        params={"charge": charge},
    )
    print(f"Inferred ligand charge for {ligand_name}: {charge}")

# Prepare a protein cutout arbitrarily using the first ligand as the reference, so we can
# determine the residues to include in the project properties.
reference_ligand_base64data = prom.molecule.pdb(
    MoleculeToPdbRequest(
        molecule=MoleculeInput(
            base64data=base64encode(ligand_sdf_texts[0]),
            filetype="sdf",
        )
    )
)
cutout = prom.preparation.cutout(
    PrepareCutoutRequest(
        pdb_base64=protein_base64data,
        ligand_pdb_base64=reference_ligand_base64data,
        cutoff=5.0,
        include_fragments=True,
        neutral_termini=False,
    )
)

print()
print(f"Protein charge: {cutout.protein_charge}")
print(f"Number of protein fragments: {len(cutout.fragments)}")
print(f"Number of protein atoms: {cutout.number_of_protein_atoms}")
print(f"Number of non-protein atoms: {cutout.number_of_non_protein_atoms}")

protein_residues = []
for residue in cutout.protein_residues:
    print(f"Included protein residue: {residue.ordinal_name} - {residue.residue_name}")
    protein_residues.append(residue.ordinal_name)

# Load the Quantum Chemical Scoring (QCScore) project properties from json and configure the protein.
with open(os.path.join(molecules_dir, "qcscore-properties.json"), "r") as f:
    project_properties_json = json.load(f)

project_properties_json["protein"]["base64data"] = protein_base64data
project_properties_json["complex_settings"]["mandatory_residues"] = protein_residues
project_properties = QuantumChemicalScoringProjectProperties(**project_properties_json)

# Create the QCScore project.
qcscore_project = prom.projects.create(
    project_request=CreateQuantumChemicalScoringProjectRequest(
        name="t4lysozyme_uvt",
        kind="QuantumChemicalScoring",
        description="QCScore project example for t4lysozyme_uvt",
        properties=project_properties,
    )
)
print()
print(f"Project '{qcscore_project.name}' created with ID: {qcscore_project.id}")

# Create workflows for each ligand.
project_workflow_ids = []
for ligand_name, ligand_input in ligand_name_to_molecule_input.items():
    # The workflow resources must be created with the same project settings.
    # Copy the project properties but rename the protein since that is configured
    # as an input molecule.
    workflow_properties = project_properties.model_dump()
    workflow_properties["molecule_a"] = ligand_input.model_dump()
    workflow_properties["molecule_b"] = workflow_properties.pop("protein")

    ligand_workflow = prom.projects.create_resource(
        id=qcscore_project.id,
        kind=ProjectResourceKind.Workflow,
        properties=CreateWorkflowRequestUnion(
            root=CreateFragmentedInteractionEnergyRequest(
                name=ligand_name,
                kind=WorkflowKind.FragmentedInteractionEnergy.value,
                parameters=FragmentedInteractionEnergyInputSpec(**workflow_properties),
                resources=ResourceRequest(gpu_type=gpu_type, gpu_count=1),
            )
        )
    )
    project_workflow_ids.append(ligand_workflow.properties.id)
    print(f"Project resource '{ligand_workflow.name}' created with workflow ID: {ligand_workflow.properties.id}")

# Wait for all workflows to complete.
print()
print("Waiting for project workflows to complete...")
for workflow_id in project_workflow_ids:
    prom.workflows.wait(workflow_id)
    workflow = prom.workflows.get(workflow_id)
    print(f"Workflow '{workflow.name}' completed with status {workflow.status.value} in {workflow.duration_seconds:.2f}s")

# Print the QCScore project results.
project_results = prom.projects.results(id=qcscore_project.id, size=len(project_workflow_ids))
ligand_scores = []
ligand_errors = []
for workflow_result in project_results.items:
    ligand_name = workflow_result.name
    if hasattr(workflow_result.results.root.results, "score"):
        ligand_score = workflow_result.results.root.results.score * KCAL_PER_MOL_PER_HARTREE
        ligand_scores.append((ligand_name, ligand_score))
    else:
        ligand_errors.append(ligand_name)

print()
print("                      ligand |            score ")
print("-----------------------------+------------------")
for name, score in sorted(ligand_scores, key=lambda x: x[1]):
    print(f"{name:>28s} | {score:16.8f}")

for name in ligand_errors:
    print(f"{name:>28s} |              --- ")

# This script will print a table which looks like this (with minor numerical differences):
"""
                      ligand |            score
-----------------------------+------------------
               butyl benzene |     -36.55239434
            isobutyl benzene |     -36.45737299
              propyl benzene |     -33.25875545
  ortho methyl ethyl benzene |     -32.21287421
   para methyl ethyl benzene |     -31.89691089
   meta methyl ethyl benzene |     -30.85640645
               ethyl benzene |     -29.45262099
                    o-xylene |     -27.30159450
                    m-xylene |     -26.55657866
                    p-xylene |     -26.29805093
              methyl benzene |     -25.54852254
                     benzene |     -21.99425084
"""
