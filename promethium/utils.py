import base64
import binascii
from datetime import datetime
from enum import Enum
import time
from typing import Optional, Union

from httpx import Client
from pydantic import UUID4

from promethium.exceptions import ClientError


NON_TERMINAL_STATUSES = ["RUNNING"]
TERMINAL_STATUSES = ["SUCCEEDED", "FAILED", "CANCELED", "COMPLETED"]


class LogEventType(str, Enum):
    STATE_CHANGES = "STATE_CHANGES"


class Base64DecodeError(Exception):
    pass


def base64encode(to_encode: Union[str, bytes]) -> str:
    return base64.b64encode(
        to_encode.encode("utf8") if isinstance(to_encode, str) else to_encode
    ).decode("utf8")


def base64decode(to_decode: str, decoding: Optional[str] = "utf8") -> Union[str, bytes]:
    try:
        tmp = base64.b64decode(to_decode.encode("utf8"))
    except binascii.Error as e:
        raise Base64DecodeError(f"Unable to base64-decode: {to_decode}: {str(e)}")
    # Optionally decode, else return as bytes:
    return tmp.decode(decoding) if decoding else tmp


def decode_artifact(artifact: dict):
    if artifact["encoding"] == "base64":
        return base64decode(artifact["base64data"])
    else:
        raise ValueError(f"Encoding type {artifact['encoding']} not supported")


def wait_for_workflows_to_complete(
    client: Client,
    workflow_ids: list[UUID4],
    log_events: list[LogEventType] = [],
    interval: int = 10,
    timeout: int = 3600,
) -> dict:
    def _should_log(state_change: bool, log_events: list[LogEventType]) -> bool:
        return "STATE_CHANGES" in log_events and state_change

    poll = True
    st = time.time()
    last_state = {str(workflow_id): None for workflow_id in workflow_ids}
    responses = {str(workflow_id): None for workflow_id in workflow_ids}
    while poll:
        # Note: no fault tolerance for failures.
        responses_statuses = {}
        for workflow_id in workflow_ids:
            response = client.get(f"/v0/workflows/{workflow_id}")
            # Add retryable:
            response.raise_for_status()
            tmp_status = response.json()["status"]
            responses_statuses[str(workflow_id)] = tmp_status
            state_change = last_state[str(workflow_id)] != tmp_status
            if _should_log(state_change, log_events):
                print(
                    f"{datetime.now().isoformat()}: Workflow status (id = {workflow_id}): {tmp_status}"
                )
            if tmp_status in TERMINAL_STATUSES:
                responses[str(workflow_id)] = response.json()
            if (time.time() - st) > timeout:
                raise TimeoutError("Timeout waiting for workflow to complete")
            last_state[str(workflow_id)] = tmp_status
        if all([response is not None for response in responses.values()]):
            poll = False
            return responses
        time.sleep(interval)
    raise ClientError("Error waiting for workflows to complete")