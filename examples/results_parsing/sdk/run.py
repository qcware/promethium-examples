import io
import gzip
import json
import os
import pathlib
import zipfile

from promethium_sdk.utils import base64encode
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateGeometryOptimizationWorkflowRequest,
)

GPU_TYPE = "a100"
INPUT_FOLDER = pathlib.Path(__file__).parent.resolve()
OUTPUT_FOLDER = "output"

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

with open(os.path.join(INPUT_FOLDER, "paxlovid.xyz"), "r") as f:
    mol = base64encode(f.read())


go_name = "paxlovid_api_geomopt"
job_params = {
    "name": go_name,
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {"base64data": mol, "filetype": "xyz"},
        "system": {
            "params": {
                "methodname": "hf-3c",
                "basisname": "MINIX",
                "xc_grid_scheme": "SG1",
                "threshold_pq": 1.0e-12,
            },
        },
        "hf": {
            "params": {
                "multiplicity": 1,
                "charge": 0,
                # Loose convergence criteria for demo purposes:
                "g_convergence": 1.0e-4,
                "print_level": 0,
            },
        },
        "pes": {
            "params": {"coordinate_system_name": "redundant"},
        },
        "optimization": {
            "params": {"maxiter": 10, "g_convergence": 4.5e-4},
            "outputs": {"gradient": False, "vibrational_frequencies": False},
        },
    },
    "resources": {"gpu_type": GPU_TYPE},
}

prom = PromethiumClient()
go_payload = CreateGeometryOptimizationWorkflowRequest(**job_params)
go_workflow = prom.workflows.submit(go_payload)
print(f"Workflow submitted (id: {go_workflow.id})")
# Optimization takes a couple of minutes:
prom.workflows.wait(go_workflow.id)

go_workflow = prom.workflows.get(go_workflow.id)
print(f"Workflow {go_workflow.name} completed with status: {go_workflow.status}")
print(f"Workflow completed in {go_workflow.duration_seconds:.2f}s")

go_results = prom.workflows.results(go_workflow.id)
with open(os.path.join(OUTPUT_FOLDER, f"{go_workflow.name}_results.json"), "w") as fp:
    fp.write(go_results.model_dump_json(indent=2))

# Numeric results:
energy = go_results.results["optimization"]["energy"]
molecule_str = go_results.get_artifact("optimized-molecule")

# (1) Approach 1:
# Download to ZIP, save to file, and extract the contents.

# Write the ZIP file to disk:
zipfile_path = os.path.join(OUTPUT_FOLDER, "example-results.zip")
with open(zipfile_path, "wb") as fp:
    fp.write(prom.workflows.download(go_workflow.id))

# Unzip the downloaded file to a folder:
unzip_folder = os.path.join(OUTPUT_FOLDER, go_workflow.name)
with zipfile.ZipFile(zipfile_path, "r") as zip_ref:
    # Extract the contents to a folder, and write all individual files to disk:
    zip_ref.extractall(unzip_folder)
    # List all of the files in the archive:
    print(f"Files downloaded: {zip_ref.namelist()}")
    # [
    #   'config.json',
    #   'geometry-optimization-result.json.gz',
    #   'geometry-optimization.xyz',
    #   'manifest.json',
    #   'optimized-molecule.xyz',
    #   'results.json',
    #   'stderr.txt',
    #   'stdout.txt',
    # ]

# Load the optimization path:
with gzip.open(os.path.join(unzip_folder, "geometry-optimization-result.json.gz"), "rt") as fp:
    optimization_path = json.load(fp)

# Sequence of gradients:
gradients = [iter["gradient"] for iter in optimization_path["iteration"]]

# (2) Approach 2:
# Extract the contents of the ZIP file in memory.

zippy = zipfile.ZipFile(io.BytesIO(prom.workflows.download(go_workflow.id)), "r")

# Read the optimization path from the in-memory ZIP file and decompress it:
gzipped_optimization_path = zippy.read("geometry-optimization-result.json.gz")
with gzip.open(io.BytesIO(gzipped_optimization_path), "rt") as fp:
    optimization_path = json.load(fp)

# Read one specific artifact from the in-memory ZIP file:
optimized_molecule_str = zippy.read("optimized-molecule.xyz")

# Read the log file:
stdout = zippy.read("stdout.txt")
print(f"Workflow log: {stdout.decode('utf-8')}")

# Read the results:
results = json.loads(zippy.read("results.json"))

# Clean up the ZIP file:
zippy.close()