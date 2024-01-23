import json
import os
import numpy as np

from promethium_sdk.client import PromethiumClient
try:
    from promethium_sdk.models import (
        CreateFSAPTCalculationWorkflowRequest,
    )
except ImportError:
    raise ImportError((
        "Unable to import CreateFSAPTCalculationWorkflowRequest, "
        "please ensure you have version >= 0.3.0 of the Promethium SDK installed."))

from promethium_sdk.utils import (
    base64encode,
)

foldername = "output"
base_url = os.getenv("PM_API_BASE_URL", "https://api.promethium.qcware.com")
gpu_type = os.getenv("PM_GPU_TYPE", "a100")

if not os.path.exists(foldername):
    os.makedirs(foldername)

monomerA = base64encode(
"""
 C   -3.794947367454    0.447388712628    1.782117979176
 H   -3.116947367454    0.417388712628    0.936117979176
 C   -3.079947367454   -0.189611287372    2.980117979176
 H   -3.656947367454    0.000388712628    3.885117979176
 H   -3.043947367454   -1.272611287372    2.822117979176
 C   -1.663947367454    0.362388712628    3.132117979176
 H   -1.193947367454   -0.126611287372    3.988117979176
 H   -1.094947367454    0.152388712628    2.216117979176
 H   -1.716947367454    1.445388712628    3.296117979176
 H   -4.717057367454   -0.113771287372    1.570427979176
 H   -4.053713367454    1.505588712628    1.934627979176
"""
)

monomerB = base64encode(
"""
 C    1.557052632546   -0.992611287372   -2.697882020824
 O    1.911052632546   -1.970611287372   -2.060882020824
 N    1.133052632546    0.132388712628   -2.093882020824
 C    1.046052632546    0.445388712628   -0.687882020824
 C    0.327052632546    1.779388712628   -0.523882020824
 C    2.401052632546    0.545388712628   -0.072882020824
 C    0.288052632546   -0.560611287372    0.118117979176
 H    0.829052632546    0.878388712628   -2.666882020824
 H    0.863052632546    2.560388712628   -1.070882020824
 H   -0.680947367454    1.653388712628   -0.930882020824
 H    0.272052632546    2.035388712628    0.542117979176
 H    0.762052632546   -1.528611287372   -0.003882020824
 H    0.326052632546   -0.236611287372    1.165117979176
 H   -0.716947367454   -0.543611287372   -0.263882020824
 H    2.243052632546    0.765388712628    0.980117979176
 H    2.925052632546    1.338388712628   -0.578882020824
 H    2.887052632546   -0.417611287372   -0.206882020824
 H    1.575032632546   -0.951611287372   -3.796971020824
"""
)

wf_name = "fsapt-test"
fsapt_wf = CreateFSAPTCalculationWorkflowRequest(**{
  "name": wf_name,
  "version": "v1",
  "kind": "FSAPTCalculation",
  "parameters": {
        "molecule_a": {
            "base64data": monomerA,
            "filetype": "xyz",
            "params": {
                "charge": 0,
                "fragments": [[0, 1, 9, 10], [2, 3, 4], [5, 6, 7, 8]],
                "fragment_names": ["A1", "A2", "A3"]
            }
        },
        "molecule_b": {
            "base64data": monomerB,
            "filetype": "xyz",
            "params": {
                "charge": 0,
                "fragments": [[0, 1, 2, 7, 17], [3, 4, 5, 8, 9, 10, 14, 15, 16], [6, 11, 12, 13]],
                "fragment_names": ["B1", "B2", "B3"]
            }
        },
        "system": {
            "params": {
                "basisname": "def2-svp",
                "methodname": "hf",
                "threshold_pq": 1e-12
            }
        },
        "jk_builder": {
            "type": "core_dfjk",
#            "type": "dfj_grid_k",
#            "type": "numerical_jk",
            "params": {}
        },
        "hf": {
            "params": {
                "g_convergence": 1.0e-6
            }
        }
  },
  "resources": {
    "gpu_type": "a100",
    "gpu_count": 1
  }
})

prom = PromethiumClient()
workflow = prom.workflows.submit(fsapt_wf)
prom.workflows.wait(workflow.id)

workflow = prom.workflows.get(workflow.id)
print(f"Workflow {workflow.name} completed with status: {workflow.status}")
print(f"Workflow completed in {workflow.duration_seconds:.2f}s")


response = prom.workflows.results(workflow.id).model_dump()
labels_a = response['results']['fsapt']['fragment_labels']['molecule_a']
labels_b = response['results']['fsapt']['fragment_labels']['molecule_b']

Eelst = 627.5095 * np.array(response['results']['fsapt']['tensors']['Eelst'])
Eexch = 627.5095 * np.array(response['results']['fsapt']['tensors']['Eexch'])
EindAB = 627.5095 * np.array(response['results']['fsapt']['tensors']['EindAB'])
EindBA = 627.5095 * np.array(response['results']['fsapt']['tensors']['EindBA'])
Edisp = 627.5095 * np.array(response['results']['fsapt']['tensors']['Edisp'])
Esapt = 627.5095 * np.array(response['results']['fsapt']['tensors']['Esapt'])

print('')
print('F-SAPT Analysis (kcal / mol)')
print('')
print('Frag1     Frag2         Elst     Exch    IndAB    IndBA     Disp    Total')
for i in range(len(labels_a)):
    for j in range(len(labels_b)):
        print('%-9s %-9s %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf' % (labels_a[i], labels_b[j], Eelst[i,j], Eexch[i,j], EindAB[i,j], EindBA[i,j], Edisp[i,j], Esapt[i,j]))

for i in range(len(labels_a)):
    print('%-9s %-9s %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf' % (labels_a[i], 'All', np.sum(Eelst, axis=1)[i], np.sum(Eexch, axis=1)[i], np.sum(EindAB, axis=1)[i], np.sum(EindBA, axis=1)[i], np.sum(Edisp, axis=1)[i], np.sum(Esapt, axis=1)[i]))

for i in range(len(labels_b)):
    print('%-9s %-9s %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf' % ('All', labels_b[i], np.sum(Eelst, axis=0)[i], np.sum(Eexch, axis=0)[i], np.sum(EindAB, axis=0)[i], np.sum(EindBA, axis=0)[i], np.sum(Edisp, axis=0)[i], np.sum(Esapt, axis=0)[i]))

print('%-9s %-9s %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf %8.3lf' % ('All', 'All', np.sum(Eelst), np.sum(Eexch), np.sum(EindAB), np.sum(EindBA), np.sum(Edisp), np.sum(Esapt)))

