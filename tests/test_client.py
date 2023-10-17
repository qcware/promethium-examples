from typing import Generator

from httpx import Response
import pytest
import respx

from promethium.client import PromethiumClient
from promethium.models import ListFileMetadataParams, PageFileMetadata

FILES_MOCK = {
    "items": [
        {
            "id": "87872307-fce7-45f6-866f-791c3b18b697",
            "name": "foo-pl2-config.json",
            "parent_id": "6e558035-7103-43b2-b9cf-88ac6dc12804",
            "is_directory": False,
            "created_at": "2023-09-26T19:38:53.437280+00:00",
            "size_bytes_uncompressed": 1046,
            "sha256_uncompressed": "27e6518672ce005784b15de1b028c15d6caca233fc640c1ed279eac2dc735bef",
        },
        {
            "id": "f063a70f-0b62-4b49-90ab-770b6029c6a8",
            "name": "benzaldehyde-9ae2.xyz",
            "parent_id": "6e558035-7103-43b2-b9cf-88ac6dc12804",
            "is_directory": False,
            "created_at": "2023-09-25T05:05:49.179868+00:00",
            "size_bytes_uncompressed": 567,
            "sha256_uncompressed": "d54fbf47281d96216120d3ba394df832d04b31082b8fefbcd9d33453be5e591c",
        },
    ],
    "total": 2,
    "page": 1,
    "size": 10,
}


@pytest.fixture
def base_url():
    return "https://test"


@pytest.fixture
def fake_api_key():
    return "i-am-not-a-real-api-key"


@pytest.fixture
def client(base_url, fake_api_key) -> Generator[None, None, PromethiumClient]:
    pc = PromethiumClient(base_url=base_url, api_key=fake_api_key)
    yield pc


@respx.mock(assert_all_mocked=False)
def test_file_list(client: PromethiumClient, base_url, respx_mock):
    respx_mock.get(f"{base_url}/v0/files").mock(
        return_value=Response(status_code=200, json=FILES_MOCK)
    )
    # List files:
    page = client.files.list(params=ListFileMetadataParams(size=50))
    assert page == PageFileMetadata(**FILES_MOCK)
