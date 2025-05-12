import os

from promethium_sdk.utils import base64encode
from promethium_sdk.client import PromethiumClient
from promethium_sdk.models import (
    # This requires an SDK version >= 0.4.1 for the initial_guess_rotation parameter.
    CreateGeometryOptimizationWorkflowRequest,
)

# This example expects that your API Credentials have been configured and
# stored in a .promethium.ini file
# If that hasn't been completed, for instructions see:
# https://github.com/qcware/promethium-examples/tree/main#configuring-your-api-credentials

foldername = "output"
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

# Specify the input xyz file contents and prepare (base64encode) for API submission
# Molecule is indenofluorene
input_mol = base64encode("""32

C          0.22966        0.26242        1.74722
C         -1.11728        0.49699        1.32553
C         -1.95629        0.21706        2.48996
C         -1.45791        0.85642        0.03678
H         -2.48218        1.00673       -0.27367
C         -0.39421        0.95772       -0.83670
C         -0.36532        1.22394       -2.27426
C          0.96688        0.74086       -0.45193
C          1.29063        0.39830        0.85751
H          2.31251        0.20733        1.15838
H         -3.03160        0.25931        2.50070
H          1.72037       -1.26205        5.96923
C          0.92566       -0.95979        5.29052
C         -0.41090       -1.01040        5.72887
H         -0.63230       -1.35360        6.73720
C         -1.45504       -0.63163        4.88373
H         -2.48652       -0.67569        5.21388
C         -1.12335       -0.21349        3.61033
C          0.21442       -0.16726        3.14784
C          1.24693       -0.53685        3.99348
H          2.28071       -0.51327        3.66720
H         -1.22605        1.45369       -2.87768
H          3.83772        0.56875       -0.94040
C          3.18908        0.75588       -1.78897
C          1.81717        0.87334       -1.63724
C          1.00666        1.13765       -2.76835
C          1.52283        1.24725       -4.04369
H          0.88161        1.42172       -4.90015
C          2.90357        1.10906       -4.19309
H          3.34726        1.17969       -5.18370
C          3.72899        0.87743       -3.07665
H          4.80346        0.78342       -3.22011""")

# Uses initial_guess_rotation parameter to swap the beta HOMO for the beta LUMO. The
# initial_guess_rotation_pairs parameter applies the rotation to the the frontier orbitals only.
job_params = {
    "name": "indenofluorene_uhf_broken_symmetry",
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {"base64data": input_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": "def2-svp",
                "methodname": "lrc-wpbe",
                "xc_grid_scheme": "SG1"
            }
        },
        "hf": {
            "params": {
                "charge": 0,
                "multiplicity": 1,
                "g_convergence": 1e-06,
                "scf_type": "uhf",
                "print_level": 2,
                "level_shift_beta": 0.1,
                "level_shift_alpha": 0.2,
                "initial_guess_rotation": "swap",
                "initial_guess_rotation_pairs": 1
            }
        },
        "pes": {
            "params": {
                "coordinate_system_name": "redundant",
                "covalent_scale": 1.3,
                "directional_derivative_h": 0.01,
                "hessian_h": 0.01,
                "use_est_guess": True
            }
        },
        "jk_builder": {
            "type": "core_dfjk",
            "params": {}
        },
        "optimization": {
            "params": {
                "maxiter": 1000,
                "g_convergence": 0.00045
            },
            "outputs": {
                "gradient": False,
                "hessian": False,
                "dipole_derivatives": False,
                "vibrational_frequencies": False
            }
        },
        "scf_properties": {
            "outputs": [
                { "type": "multipole_moments", "expansion_order": 2 },
                { "type": "atomic_charges", "analysis_method": "mulliken" },
                { "type": "atomic_charges", "analysis_method": "lowdin" },
                { "type": "orbital_energies", "occupied_count": 10, "unoccupied_count": 10 },
                { "type": "polar_surface_area" }
            ]
        }
    },
    "resources": {"gpu_type": gpu_type},
}

# Instantiate the Promethium client and submit a GO workflow using the above configuration
prom = PromethiumClient()
go_payload = CreateGeometryOptimizationWorkflowRequest(**job_params)
go_workflow = prom.workflows.submit(go_payload)
print(f"Workflow {go_workflow.name} submitted with id: {go_workflow.id}")

# Wait for the workflow to finish
prom.workflows.wait(go_workflow.id)

# Get the status and Wall-clock time:
go_workflow = prom.workflows.get(go_workflow.id)
print(f"Workflow {go_workflow.name} completed with status: {go_workflow.status}")
print(f"Workflow completed in {go_workflow.duration_seconds:.2f}s")

# Obtain the numeric results:
go_results = prom.workflows.results(go_workflow.id)
with open(os.path.join(foldername, f"{go_workflow.name}_results.json"), "w") as fp:
    fp.write(go_results.model_dump_json(indent=2))

# Extract and print the energy contained in the numeric results:
energy = go_results.results["optimization"]["energy"]
print(f"Energy (Hartrees) = {energy}")

# Extract and print the optimized geometry contained in the numeric results:
molecule_str = go_results.get_artifact("optimized-molecule")
print("The optimized geometry:")
print(f'{molecule_str}')

# Download results:
with open(os.path.join(foldername, f"{go_workflow.name}_results.zip"), "wb") as fp:
    fp.write(prom.workflows.download(go_workflow.id))
