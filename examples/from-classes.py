import time
from uuid import UUID

from pydantic import UUID4

from promethium.models import (
    GeometryOptimizationInputSpec,
    CreateGeometryOptimizationWorkflowRequest,
    Kind2,
    MoleculeInput,
    Hf,
    Pes,
    System,
    SystemParams,
    LBFGSOptimization,
    ResourceRequest,
    Version,
    GpuType,
    ValidFileExtensions,
)
from promethium.client import PromethiumClient
from promethium.utils import base64encode


prom = PromethiumClient()

MOL_STR = """29
17 12 0 0
C -2.20306 0.68864 2.69528
C -0.88632 -0.05265 2.4804
C -0.27088 -0.40608 3.83168
C 0.07881 0.84083 1.70461
C -1.14763 -1.33268 1.69004
H -2.91013 0.07044 3.25014
H -2.04356 1.60883 3.25946
H -2.66077 0.95014 1.74012
H 0.67228 -0.93846 3.7009
H -0.07386 0.49366 4.41648
H -0.94217 -1.04382 4.40842
H 1.02738 0.32824 1.53426
H 0.2841 1.75897 2.25804
H -0.34359 1.11932 0.73715
H -1.61137 -1.11085 0.72741
H -0.21506 -1.87108 1.5104
H -1.81814 -1.99449 2.24022
O -1.79338 -0.61133 -2.12789
C -0.69507 -0.11026 -1.95682
C -0.32949 1.26835 -2.23185
C 0.92093 1.69501 -1.96095
N 1.87152 0.86367 -1.4324
H 2.79272 1.20097 -1.20806
C 1.64017 -0.46611 -1.12317
O 2.48119 -1.18685 -0.6229
N 0.36347 -0.87384 -1.44557
H 0.14658 -1.83443 -1.21708
H -1.07236 1.92888 -2.64433
H 1.23924 2.71094 -2.14165
"""

# Submit a workflow:
config = {
    "name": "client-example-geometry-optimization",
    "version": "v1",
    "kind": "GeometryOptimization",
    "parameters": {
        "molecule": {
            "id": str(file_id),
        },
        "system": {
            "params": {
                "basisname": "def2-tzvp",
                "jkfit_basisname": "def2-universal-jkfit",
                "xc_functional_name": "b3lyp",
                "xc_grid_scheme": "SG2",
            }
        },
        "hf": {
            "params": {
                "multiplicity": 1,
                "charge": 0,
                "g_convergence": 1.0e-8,
                "print_level": 2,
            }
        },
        "pes": {"params": {"coordinate_system_name": "redundant"}},
        "optimization": {
            "params": {"maxiter": 20},
            "outputs": {"gradient": False, "vibrational_frequencies": True},
        },
    },
    "resources": {"gpu_type": "a100"},
}
payload = CreateGeometryOptimizationWorkflowRequest(
    name="class-example-geometry-optimization",
    version=Version.v1,
    kind=Kind2.GeometryOptimization,
    parameters=GeometryOptimizationInputSpec(
        molecule=MoleculeInput(
            id=None,
            base64data=base64encode(MOL_STR),
            filetype=ValidFileExtensions.smi,
            filename=None
        ),
        system=System(
            params=SystemParams(**{
                "basisname": "def2-tzvp",
                "jkfit_basisname": "def2-universal-jkfit",
                "xc_functional_name": "b3lyp",
                "xc_grid_scheme": "SG2"
            }),
        hf=Hf(),
        pes=Pes(),
        optimization=LBFGSOptimization(),
    ),
    resources=ResourceRequest(gpu_type=GpuType.a100, gpu_count=1),
)