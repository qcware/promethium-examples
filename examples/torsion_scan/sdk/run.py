import os
import csv
import json
import copy

from promethium_sdk.utils import base64encode
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import CreateTorsionScanWorkflowRequest
from promethium_sdk.models import WorkflowStatus

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CSV_PATH    = os.path.join(SCRIPT_DIR, "molecules.csv")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "torsion_scan-config.json")
FOLDERNAME  = "output"

def read_file_to_string(filename: str) -> str:
    """Reads the entire content of a text file into a single string."""
    with open(filename, 'r', encoding='utf-8') as f:
        return f.read()

# Load full job config from JSON
with open(CONFIG_PATH, "r") as f:
    BASE_CONFIG = json.load(f)

print("Loaded config:")
print(json.dumps(BASE_CONFIG, indent=2))
print()

# ---------------------------------------------------------------------------
# Just In Case
# ---------------------------------------------------------------------------

def safe_name(name: str) -> str:
    """Convert a molecule name into a filesystem/job-safe string."""
    return name.strip().replace(" ", "_").replace("/", "-")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if not os.path.exists(FOLDERNAME):
    os.makedirs(FOLDERNAME)

prom = PromethiumClient()

# --- Read CSV and submit all jobs ---
workflows = []  # list of (workflow, safe_name)

print("Reading CSV and submitting torsion scan jobs...\n")

with open(CSV_PATH, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        mol_name = row["Name"]
        filename = os.path.join(SCRIPT_DIR, row["Filename"])
        atom_a   = int(row["AtomA"])
        atom_b   = int(row["AtomB"])
        atom_c   = int(row["AtomC"])
        atom_d   = int(row["AtomD"])
        torsion_indices = [atom_a, atom_b, atom_c, atom_d]
        job_name = safe_name(mol_name)

        print(f"  Preparing {mol_name}...")
        print()

        try:
            file_content_string = read_file_to_string(filename)
            molecule_str = file_content_string
            mol_base64 = base64encode(molecule_str)

            lines = file_content_string.strip().splitlines()
            num_atoms = int(lines[0].strip())
            atom_lines = lines[2:2 + num_atoms]  # skip atom count and comment line

            print(f"  Molecule read from {filename}")

            # Print header lines as-is (no index)
            print(f"  Atoms: {lines[0].strip()}")  # atom count
            print(f"  Note:  {mol_name}")  # comment line
            # Print atom lines with 0-based index
            for i, line in enumerate(atom_lines):
                print(f"  {i:<4} {line}")
            print()
            print("  Preparing Torsion Scan along the following indices")
            print("  * Please ensure that your configuration is 0-indexed *")
            print()
            for idx in torsion_indices:
                print(f"    {idx:<4} {atom_lines[idx]}")
            print()
        except Exception as e:
            print(f"  [SKIP] {mol_name}: {e}\n")
            continue

        # Deep copy the base config so each job is independent
        job_params = copy.deepcopy(BASE_CONFIG)

        # Override per-molecule fields
        job_params["name"] = job_name
        job_params["parameters"]["molecule"]["base64data"] = mol_base64
        job_params["parameters"]["molecule"]["filetype"]   = "xyz"
        job_params["parameters"]["torsion"]["constraint"]["params"] = {
            "atomA": atom_a,
            "atomB": atom_b,
            "atomC": atom_c,
            "atomD": atom_d,
        }

        payload = CreateTorsionScanWorkflowRequest(**job_params)
        print(f"  Submitting: {job_name} ... ", end="")
        workflow = prom.workflows.submit(payload)
        print(f"workflow ID {workflow.id} submitted!\n")
        workflows.append((workflow, job_name))

print(f"\nSubmitted {len(workflows)} job(s). Waiting for completion...\n")

# --- Wait for all jobs and collect results ---
for workflow, job_name in workflows:
    prom.workflows.wait(workflow.id)
    workflow = prom.workflows.get(workflow.id)

    print(f"Workflow {workflow.name} completed with status: {workflow.status}")
    print(f"  Duration: {workflow.duration_seconds:.2f}s")

    if workflow.status != WorkflowStatus.COMPLETED:
        print("  [WARNING] Job did not complete successfully, skipping results.\n")
        continue

    results = prom.workflows.results(workflow.id)

    # Save full results JSON
    out_path = os.path.join(FOLDERNAME, f"{job_name}_results.json")
    with open(out_path, "w") as fp:
        fp.write(results.model_dump_json(indent=2))
    print(f"  Results saved to {out_path}")

    # Download raw output zip
    zip_path = os.path.join(FOLDERNAME, f"{job_name}_results.zip")
    with open(zip_path, "wb") as fp:
        fp.write(prom.workflows.download(workflow.id))
    print(f"  Download saved to {zip_path}\n")

print("All done!")
