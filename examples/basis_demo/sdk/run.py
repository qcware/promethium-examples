import os

from promethium.utils import base64encode
from promethium.client import PromethiumClient
from promethium.models import (
    CreateGeometryOptimizationWorkflowRequest,
    CreateSinglePointCalculationWorkflowRequest,
)

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

mol = base64encode("""
    C        -3.61325       -0.84160        0.14457
    C        -2.25688       -0.64376       -0.57620
    F        -3.79613        0.10770        1.11447
    F        -3.72391       -2.04496        0.76266
    F        -4.67420       -0.72119       -0.69898
    O        -1.76953       -1.45009       -1.36726
    N        -1.62790        0.56794       -0.28818
    H        -2.07454        1.18112        0.38576
    C        -0.37312        0.96581       -0.92863
    C        -0.33762        2.49586       -1.27026
    C         0.91023        0.40898       -0.23574
    H        -0.36776        0.44052       -1.89614
    C        -0.49664        3.40496       -0.04162
    C        -1.49008        2.81571       -2.25219
    C         0.98264        2.87264       -1.97424
    H         1.83977        2.78616       -1.29799
    H         0.95982        3.91011       -2.32816
    H         1.16560        2.23196       -2.84389
    H        -2.47022        2.61940       -1.80417
    H        -1.41048        2.21284       -3.16399
    H        -1.47511        3.86999       -2.55226
    H        -1.44156        3.22943        0.48168
    H        -0.48841        4.46205       -0.33386
    H         0.32230        3.26508        0.66698
    O         1.90595        0.17131       -0.93712
    N         1.00100        0.23009        1.12514
    C         0.01924        0.57566        2.14061
    C         2.24490       -0.30950        1.72385
    H         3.12336        0.15791        1.26489
    C         2.34253       -1.84974        1.51322
    C         2.14140        0.06112        3.18805
    H        -0.45172        1.53611        1.93687
    C         0.77225        0.60289        3.43283
    H        -0.74139       -0.21158        2.16107
    H         0.19484        0.22099        4.26502
    C         1.98665        1.48144        3.71428
    C         2.33564        1.71548        5.16577
    C         2.32636        2.65435        2.83224
    H         2.55572       -0.68006        3.86007
    H         2.19488        2.45741        1.76706
    H         3.37413        2.94069        2.97515
    H         1.70084        3.51416        3.09361
    H         2.07401        0.85765        5.79484
    H         1.79954        2.58944        5.54983
    H         3.41071        1.89356        5.27426
    O         2.41423       -2.65426        2.43991
    N         2.40832       -2.24659        0.19623
    H         2.35091       -1.52225       -0.52060
    C         2.37689       -3.63929       -0.24312
    C         1.13234       -4.32267        0.18665
    H         2.35866       -3.56699       -1.33426
    C         3.64249       -4.40448        0.19648
    N         0.16610       -4.87717        0.51411
    H         4.52339       -3.82786       -0.11807
    C         3.74598       -5.82843       -0.35203
    H         3.68926       -4.46063        1.29109
    C         4.98159       -6.58105        0.16390
    H         2.84883       -6.41303       -0.11557
    C         3.95731       -5.89666       -1.85162
    N         4.82278       -6.93442       -2.11017
    H         5.84230       -5.90382        0.23727
    C         5.23309       -7.61310       -0.91964
    H         4.82369       -7.03496        1.14670
    H         5.01368       -7.22264       -3.06214
    H         4.60618       -8.50157       -0.79514
    H         6.28295       -7.90612       -0.99587
    O         3.42325       -5.20351       -2.69779"""
)

go_name = "paxlovid_api_geomopt"
job_params = {
    "name": go_name,
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {"base64data": mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": "def2-svp",
                "jkfit_basisname": "def2-universal-jkfit",
                "xc_functional_name": "b3lyp",
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

prom = PromethiumClient()
go_payload = CreateGeometryOptimizationWorkflowRequest(**job_params)
go_workflow = prom.workflows.submit(go_payload)

prom.workflows.wait(go_workflow.id)

go_workflow = prom.workflows.get(go_workflow.id)
print(f"Workflow {go_workflow.name} completed with status: {go_workflow.status}")
print(f"Workflow completed in {go_workflow.duration_seconds:.2f}s")

go_results = prom.workflows.results(go_workflow.id)
with open(f"{foldername}/{go_workflow.name}_results.json", "w") as fp:
    fp.write(go_results.model_dump_json(indent=2))

# Numeric results:
energy = go_results.results["optimization"]["energy"]
molecule_str = go_results.get_artifact("optimized-molecule")
print(energy)
print(molecule_str)

# Download:
prom.workflows.download(go_workflow.id)

# Re-encode the molecule:
opt_mol = base64encode(molecule_str)

# SPC: SinglePointCalculation
spc_name = "paxlovid_api_spe"
job_params = {
    "name": spc_name,
    "version": "v1",
    "kind": "SinglePointCalculation",
    "parameters": {
        "molecule": {"base64data": opt_mol, "filetype": "xyz"},
        "system": {
            "params": {
                "basisname": "def2-tzvp",
                "jkfit_basisname": "def2-universal-jkfit",
                "xc_functional_name": "b3lyp",
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
        "pes": {
            "params": {"coordinate_system_name": "redundant"},
        },
        "optimization": {
            "params": {"maxiter": 200, "g_convergence": 1.0e-4},
            "outputs": {"gradient": False, "vibrational_frequencies": False},
        },
    },
    "resources": {"gpu_type": gpu_type},
}

spc_payload = CreateSinglePointCalculationWorkflowRequest(**job_params)
print(f"Submitting {spc_name}...", end="")
spc_workflow = prom.workflows.submit(spc_payload)

prom.workflows.wait(spc_workflow.id)

spc_workflow = prom.workflows.get(spc_workflow.id)
print(f"Workflow {spc_workflow.name} completed with status: {spc_workflow.status}")
print(f"Workflow completed in {spc_workflow.duration_seconds:.2f}s")

spc_results = prom.workflows.results(spc_workflow.id)
with open(f"{foldername}/{spc_workflow.name}_results.json", "w") as fp:
    fp.write(spc_results.model_dump_json(indent=2))

# Numeric results:
energy = spc_results.results["rhf"]["energy"]
print(energy)

# Download:
prom.workflows.download(go_workflow.id)
