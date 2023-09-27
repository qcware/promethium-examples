import uuid

import httpx
from pydantic import UUID4
import pytest
import respx

from promethium.utils import (
    base64decode,
    base64encode,
    decode_artifact,
    wait_for_workflows_to_complete,
    LogEventType,
)

PROMETHIUM_API_BASE_URL = "https://test"
FAKE_API_KEY = "not-a-real-api-key"


def test_base64encode():
    assert base64encode("foo") == "Zm9v"
    assert base64encode(b"foo") == "Zm9v"


def test_base64decode():
    assert base64decode("Zm9v") == "foo"
    assert base64decode("Zm9v", decoding=None) == b"foo"


@pytest.fixture
def client():
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": FAKE_API_KEY,
    }
    return httpx.Client(base_url=PROMETHIUM_API_BASE_URL, headers=headers)


@pytest.fixture
def workflow_id():
    return uuid.uuid4()


@respx.mock
def test_wait_for_workflows_to_complete_state_change(
    workflow_id: UUID4, client: httpx.Client, capsys
):
    route = respx.get(f"{PROMETHIUM_API_BASE_URL}/v0/workflows/{workflow_id}")
    route.side_effect = [
        httpx.Response(200, json={"status": "RUNNING"}),
        httpx.Response(200, json={"status": "RUNNING"}),
        httpx.Response(200, json={"status": "COMPLETED"}),
    ]
    # Capture stdout and check for expected output:
    workflows = wait_for_workflows_to_complete(
        client=client,
        workflow_ids=[workflow_id],
        interval=1,
        log_events=[LogEventType("STATE_CHANGES")],
    )
    assert workflows[str(workflow_id)]["status"] == "COMPLETED"
    captured = capsys.readouterr()
    words = captured.out.split()
    assert words.count("RUNNING") == 1
    assert words.count("COMPLETED") == 1


@respx.mock
def test_wait_for_workflows_to_complete_timeout(
    workflow_id: UUID4, client: httpx.Client, capsys
):
    route = respx.get(f"{PROMETHIUM_API_BASE_URL}/v0/workflows/{workflow_id}")
    route.side_effect = [
        httpx.Response(200, json={"status": "RUNNING"}),
        httpx.Response(200, json={"status": "RUNNING"}),
        httpx.Response(200, json={"status": "RUNNING"}),
        httpx.Response(200, json={"status": "RUNNING"}),
        httpx.Response(200, json={"status": "COMPLETED"}),
    ]
    # Capture stdout and check for expected output:
    with pytest.raises(TimeoutError):
        wait_for_workflows_to_complete(
            client=client,
            workflow_ids=[workflow_id],
            interval=1,
            timeout=4,
            log_events=["ALL"],
        )
        captured = capsys.readouterr()
        words = captured.out.split()
        assert words.count("RUNNING") == 4
        assert words.count("COMPLETED") == 0


@respx.mock
def test_workflow_success_and_decode(workflow_id: UUID4, client: httpx.Client, capsys):
    OPTIMIZED_MOLECULE = """14

O                2.878375420200    -0.324262510357    -0.000299891767
C                0.556064657824     0.225168455594    -0.000021433248
C               -0.354522130060     1.282458754632    -0.000038686697
C                0.090467174044    -1.092825951923     0.000009244950
C               -1.720367044884     1.029176100308     0.000034502322
C               -1.271356842725    -1.344674212985    -0.000058026634
C               -2.177073599784    -0.283989405453    -0.000000516625
C                2.006194686562     0.511945162578    -0.000014467455
H                0.012691519357     2.302668614583    -0.000040152834
H                0.811782421519    -1.899482495901    -0.000013417293
H               -2.425772805423     1.850003063946     0.000050193089
H               -1.634065325963    -2.364523524101    -0.000079193804
H               -3.241157260903    -0.484082187221     0.000005039757
H                2.261439130259     1.592320136427    -0.000333193766"""
    result = {
        "id": "7e78d1af-a6e4-4489-8ef2-87ab5d754037",
        "kind": "GeometryOptimization",
        "api_version": "v1",
        "status": "COMPLETED",
        "results": {
            "rhf": {},
            "optimization": {"converged": True, "energy": -345.70823352070454},
            "exceptions": {},
            "artifacts": {
                "optimized-molecule": {
                    "encoding": "base64",
                    "base64data": base64encode(OPTIMIZED_MOLECULE),
                    "filetype": "xyz",
                }
            },
        },
    }
    respx.get(f"{PROMETHIUM_API_BASE_URL}/v0/workflows/{workflow_id}/results").mock(
        return_value=httpx.Response(200, json=result)
    )
    assert (
        decode_artifact(result["results"]["artifacts"]["optimized-molecule"])
        == OPTIMIZED_MOLECULE
    )
