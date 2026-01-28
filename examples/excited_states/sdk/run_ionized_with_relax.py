import os

from promethium_sdk.utils import base64encode
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    CreateGeometryOptimizationWorkflowRequest,
    CreateSinglePointCalculationWorkflowRequest,
)

# This script:
# - Optimizes the molecule in the neutral ground state
# - Performs a single point calculation in the ionized state (q=+1, multiplicity=2)
# - Performs a geometry optimization in the ionized state (q=+1, multiplicity=2)
# - Performs a single point calculation at the geometry of the optimized ionized state in the neutral ground state

# Set to high memory GPUs so less chance of job crashing due to insufficient memory
gpu_type = os.getenv("PM_GPU_TYPE", "a100-80gb")

foldername = "ionized_molecules"
os.makedirs(foldername, exist_ok=True)

prom = PromethiumClient()

# Set molecule name and data to use
molecule_id = "molecule_name"
init_mol = base64encode("""3

    O          0.68657       -1.48867        0.00000
    H          1.65657       -1.48867        0.00000
    H          0.36324       -2.12337       -0.65842"""
)

# Set DFT methods for geometry optimization (go) and single point energy calculation (spc)
xcfunctional_go = "pbe33"
basisset_go = "def2-svp"
xcfunctional_spc = "pbe33"
basisset_spc = "def2-svp"

# Set up the geometry optimization of the ground state
go_gs_name = f"{molecule_id}_go_gs"
job_params = {
    "name": go_gs_name,
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {"base64data": init_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": basisset_go,
                "jkfit_basisname": "def2-universal-jkfit",
                "methodname": xcfunctional_go,
                "xc_grid_scheme": "SG1",
                "threshold_pq": 1.0e-12
            },
        },
        "hf": {
            "params": {
                "multiplicity": 1,
                "charge": 0,
                "g_convergence": 1.0e-6,
                "print_level": 0,
            },
        },
        "pes": {
            "params": {"coordinate_system_name": "redundant"},
        },
        "optimization": {
            "params": {"maxiter": 200, "g_convergence": 4.5e-4},
            "outputs": {"gradient": False, "vibrational_frequencies": False},
        },
    },
    "resources": {"gpu_type": gpu_type},
}

print(f"Submitting {go_gs_name} geometry optimization in ground state q=0, m=1...", end="")
go_gs_payload = CreateGeometryOptimizationWorkflowRequest(**job_params)
go_gs_workflow = prom.workflows.submit(go_gs_payload)
print("done!")

# Wait on the go_gs workflow, then run the SPC-ionized state and the GO-ionized state
prom.workflows.wait(go_gs_workflow.id)
go_gs_workflow = prom.workflows.get(go_gs_workflow.id)
print(f"Workflow {go_gs_workflow.name} completed with status: {go_gs_workflow.status}")
print(f"Workflow completed in {go_gs_workflow.duration_seconds:.2f}s")

# Download geometry optimization results as json and optimized molecule xyz
go_gs_results = prom.workflows.results(go_gs_workflow.id)
with open(os.path.join(foldername, f"{go_gs_workflow.name}_results.json"), "w") as fp:
    fp.write(go_gs_results.model_dump_json(indent=2))
opt_gs_molecule_str = go_gs_results.get_artifact("optimized-molecule")
with open(os.path.join(foldername, f"{go_gs_workflow.name}.xyz"), "w") as fp:
    fp.write(opt_gs_molecule_str)

# Output the energy from the results
go_gs_energy = go_gs_results.results["optimization"]["energy"]
print(f"Ground state energy at ground state geometry is: {go_gs_energy}")

# Launch spc based on the geometry optimization output
# SPC: single point calculation at ionized state (spc_Is)
# Note: using charge=1,multiplicity=2
opt_gs_mol = base64encode(opt_gs_molecule_str)
spc_Is_name = f"{molecule_id}_spc_Is"
job_params = {
    "name": spc_Is_name,
    "version": "v1",
    "kind": "SinglePointCalculation",
    "parameters": {
        "molecule": {"base64data": opt_gs_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": basisset_spc,
                "jkfit_basisname": "def2-universal-jkfit",
                "methodname": xcfunctional_spc,
                "xc_grid_scheme": "SG1",
                "threshold_pq": 1.0e-12,
            },
        },
        "hf": {
            "params": {
                "multiplicity": 2,
                "charge": 1,
                "g_convergence": 1.0e-6,
                "print_level": 0,
            },
        },
        "scf_properties": {
            "outputs": [{
                    "type": "multipole_moments",
                    "expansion_order": 2
                },
                {
                    "type": "atomic_charges",
                    "analysis_method": "mulliken"
                },
                {
                    "type": "atomic_charges",
                    "analysis_method": "lowdin"
                },
                {
                    "type": "orbital_energies",
                    "occupied_count": 10,
                    "unoccupied_count": 10,
                    "generate_msgpack": True
                },
                {
                    "type": "polar_surface_area"
                }]
        },
    },
    "resources": {"gpu_type": gpu_type},
}

print(f"Submitting {spc_Is_name} with charge=+1 and multiplicity=2 at ground state geometry...", end="")
spc_Is_payload = CreateSinglePointCalculationWorkflowRequest(**job_params)
spc_Is_workflow = prom.workflows.submit(spc_Is_payload)
print("done!")

# Proceed to set up the geometry optimization of the ionized state
# using charge=+1 and multiplicity=2
go_Is_name = f"{molecule_id}_go_Is"
job_params = {
    "name": go_Is_name,
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {"base64data": opt_gs_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": basisset_go,
                "jkfit_basisname": "def2-universal-jkfit",
                "methodname": xcfunctional_go,
                "xc_grid_scheme": "SG1",
                "threshold_pq": 1.0e-12
            },
        },
        "hf": {
            "params": {
                "multiplicity": 2,
                "charge": 1,
                "g_convergence": 1.0e-6,
                "print_level": 0,
            },
        },
        "pes": {
            "params": {"coordinate_system_name": "redundant"},
        },
        "optimization": {
            "params": {"maxiter": 200, "g_convergence": 4.5e-4},
            "outputs": {"gradient": False, "vibrational_frequencies": False},
        },
    },
    "resources": {"gpu_type": gpu_type},
}

print(f"Submitting {go_Is_name} geometry optimization at ionized state q=+1, m=2...", end="")
go_Is_payload = CreateGeometryOptimizationWorkflowRequest(**job_params)
go_Is_workflow = prom.workflows.submit(go_Is_payload)
print("done!")

# Wait on the spc_Is workflow
prom.workflows.wait(spc_Is_workflow.id)
spc_Is_workflow = prom.workflows.get(spc_Is_workflow.id)
print(f"Workflow {spc_Is_workflow.name} completed with status: {spc_Is_workflow.status}")
print(f"Workflow completed in {spc_Is_workflow.duration_seconds:.2f}s")

# Save and print the spc_Is results
spc_Is_results = prom.workflows.results(spc_Is_workflow.id)
with open(os.path.join(foldername, f"{spc_Is_workflow.name}_results.json"), "w") as fp:
    fp.write(spc_Is_results.model_dump_json(indent=2))
with open(os.path.join(foldername, f"{spc_Is_workflow.name}_results.zip"), "wb") as fp:
    fp.write(prom.workflows.download(spc_Is_results.id))
spc_Is_energy = spc_Is_results.results["uhf"]["energy"]
print(f"Ionized state energy at ground state geometry is: {spc_Is_energy}")

# Wait on the go_Is workflow
prom.workflows.wait(go_Is_workflow.id)
go_Is_workflow = prom.workflows.get(go_Is_workflow.id)
print(f"Workflow {go_Is_workflow.name} completed with status: {go_Is_workflow.status}")
print(f"Workflow completed in {go_Is_workflow.duration_seconds:.2f}s")

# Save and print the go_Is results
go_Is_results = prom.workflows.results(go_Is_workflow.id)
with open(os.path.join(foldername, f"{go_Is_workflow.name}_results.json"), "w") as fp:
    fp.write(go_Is_results.model_dump_json(indent=2))
opt_Is_molecule_str = go_Is_results.get_artifact("optimized-molecule")
with open(os.path.join(foldername, f"{go_Is_workflow.name}.xyz"), "w") as fp:
    fp.write(opt_Is_molecule_str)
go_Is_energy = go_Is_results.results["optimization"]["energy"]
print(f"Ionized state energy at ionized state geometry is: {go_Is_energy}")

# Launch spc based on the geometry optimization at the ionized state
# SPC: single point calculation at ionized geometry opt state (spc_gs)
# Note: using charge=0,multiplicity=1
opt_Is_mol = base64encode(opt_Is_molecule_str)
spc_gs_name = f"{molecule_id}_spc_gs"
job_params = {
    "name": spc_gs_name,
    "version": "v1",
    "kind": "SinglePointCalculation",
    "parameters": {
        "molecule": {"base64data": opt_Is_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": basisset_spc,
                "jkfit_basisname": "def2-universal-jkfit",
                "methodname": xcfunctional_spc,
                "xc_grid_scheme": "SG1",
                "threshold_pq": 1.0e-12,
            },
        },
        "hf": {
            "params": {
                "multiplicity": 1,
                "charge": 0,
                "g_convergence": 1.0e-6,
                "print_level": 0,
            },
        },
        "scf_properties": {
            "outputs": [{
                    "type": "multipole_moments",
                    "expansion_order": 2
                },
                {
                    "type": "atomic_charges",
                    "analysis_method": "mulliken"
                },
                {
                    "type": "atomic_charges",
                    "analysis_method": "lowdin"
                },
                {
                    "type": "orbital_energies",
                    "occupied_count": 10,
                    "unoccupied_count": 10,
                    "generate_msgpack": True
                },
                {
                    "type": "polar_surface_area"
                }]
        },
    },
    "resources": {"gpu_type": gpu_type},
}
print(f"Submitting {spc_gs_name} with charge=0 and multiplicity=1 at ionized state geometry...", end="")
spc_gs_payload = CreateSinglePointCalculationWorkflowRequest(**job_params)
spc_gs_workflow = prom.workflows.submit(spc_gs_payload)
print("done!")

# Wait on the spc_gs workflow
prom.workflows.wait(spc_gs_workflow.id)
spc_gs_workflow = prom.workflows.get(spc_gs_workflow.id)
print(f"Workflow {spc_gs_workflow.name} completed with status: {spc_gs_workflow.status}")
print(f"Workflow completed in {spc_gs_workflow.duration_seconds:.2f}s")

# Save and print the spc_gs results
spc_gs_results = prom.workflows.results(spc_gs_workflow.id)
with open(os.path.join(foldername, f"{spc_gs_workflow.name}_results.json"), "w") as fp:
    fp.write(spc_gs_workflow.model_dump_json(indent=2))
with open(os.path.join(foldername, f"{spc_gs_workflow.name}_results.zip"), "wb") as fp:
    fp.write(prom.workflows.download(spc_gs_results.id))
spc_gs_energy = spc_gs_results.results["rhf"]["energy"]
print(f"Ground state energy at ionized state geometry is: {spc_gs_energy}")

# Print all the results at the end
print()
print("=============================================")
print(f"  Ground  state energy: {go_gs_energy}")
print(f"  Ionized state energy: {spc_Is_energy}")
print(f"  Ionized relax energy: {go_Is_energy}")
print(f"  Ground  relax energy: {spc_gs_energy}")
print("=============================================")
print()
