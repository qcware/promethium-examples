import base64
import binascii
from datetime import datetime
from enum import Enum
import time
from typing import Union, Optional

import httpx


NON_TERMINAL_STATUSES = ["RUNNING"]
TERMINAL_STATUSES = ["SUCCEEDED", "FAILED", "CANCELED", "COMPLETED"]


class Base64DecodeError(Exception):
    pass


class LogEventType(str, Enum):
    STATE_CHANGES = "STATE_CHANGES"
    POLLING = "POLLING"
    ALL = "ALL"


def wait_for_workflows_to_complete(
    client,
    workflow_ids,
    log_events = [],
    interval = 10,
    timeout = 3600,
    ):

    def _should_log(state_change, log_events):
        return (
            "POLL" in log_events
            or "ALL" in log_events
            or ("STATE_CHANGES" in log_events and state_change)
        )

    if "ALL" in log_events:
        print(f"Polling for workflow completion, workflow ids: {workflow_ids}")
    poll = True
    st = time.time()
    last_state = {workflow_id: None for workflow_id in workflow_ids}
    responses = {workflow_id: None for workflow_id in workflow_ids}
    while poll:
        # For production, recommend async requests, but for simplicity, use sync here.
        # Again, demo script so no fault tolerance for failures.
        responses_statuses = {}
        for workflow_id in workflow_ids:
            response = client.get(f"/v0/workflows/{workflow_id}")
            response.raise_for_status()
            tmp_status = response.json()["status"]
            responses_statuses[workflow_id] = tmp_status
            state_change = last_state[workflow_id] != tmp_status
            if _should_log(state_change, log_events):
                print(
                    f"{datetime.now().isoformat()}: Workflow status (id = {workflow_id}): {tmp_status}"
                )
            if tmp_status in TERMINAL_STATUSES:
                responses[workflow_id] = response.json()
            if (time.time() - st) > timeout:
                raise TimeoutError("Timeout waiting for workflow to complete")
            last_state[workflow_id] = tmp_status
        if all([response is not None for response in responses.values()]):
            poll = False
            return responses
        time.sleep(interval)

