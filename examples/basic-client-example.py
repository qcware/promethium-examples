import pandas as pd

from promethium.models import Workflow
from promethium.client import PromethiumClient


prom = PromethiumClient()

# List workflows:
for workflow_page in prom.workflows.list(kind="TorsionScan", size=10):
    print(pd.DataFrame(workflow_page))

# Grab 'em all:
workflow_list = []
for workflow_page in prom.workflows.list(kind="TorsionScan", size=10):
    workflow_list.extend(workflow_page)
all_workflows = pd.DataFrame(workflow_list)

# Pick a workflow:
workflow_id = all_workflows.iloc[0]["id"]

# Grab details of one workflow:
workflow: Workflow = prom.workflows.get(id=workflow_id)

# Grab the numeric results of one workflow:
workflow_results: dict = prom.workflows.results(id=workflow_id)

# Download results of one workflow:
#prom.workflows.download(id=workflow_id, path=".")

# Submit a workflow:
#workflow = prom.workflows.submit(workflow=Workflow(...))

# Get the status of a workflow:
#status = prom.workflows.status(id=workflow.id)

# Cancel a workflow:
#prom.workflows.stop(id=workflow.id)

# Delete a workflow:
#prom.workflows.delete(id=workflow.id)

# Wait for a workflow to finish:
#prom.workflows.wait(id=workflow.id)
