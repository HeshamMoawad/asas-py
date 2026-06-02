from typing import Any, Dict, cast

import pytest
import respx
from httpx import Response as HttpxResponse

from asas import (
    AsasAsyncClient,
    AsasClient,
    HTTPXAsyncEngine,
    HTTPXSyncEngine,
    Payload,
    Response,
    delete,
    get,
    patch,
    post,
    put,
)


class MockSyncClient(AsasClient):
    @get("/test")
    def get_test(self, response: Response) -> Dict[str, Any]:
        return cast(Dict[str, Any], response.json())

    @post("/test-post")
    def post_test(self, response: Response) -> Dict[str, Any]:
        return cast(Dict[str, Any], response.json())

    @put("/test-put")
    def put_test(self, response: Response) -> Dict[str, Any]:
        return cast(Dict[str, Any], response.json())

    @delete("/test-delete")
    def delete_test(self, response: Response) -> Dict[str, Any]:
        return cast(Dict[str, Any], response.json())

    @patch("/test-patch")
    def patch_test(self, response: Response) -> Dict[str, Any]:
        return cast(Dict[str, Any], response.json())


class MockAsyncClient(AsasAsyncClient):
    @get("/test-async")
    async def get_test_async(self, response: Response) -> Dict[str, Any]:
        return cast(Dict[str, Any], response.json())


@pytest.mark.asyncio
async def test_client_all_decorators() -> None:
    sync_client = MockSyncClient(base_url="https://api.example.com")
    async_client = MockAsyncClient(base_url="https://api.example.com")

    async with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/test").mock(return_value=HttpxResponse(200, json={"m": "g"}))
        respx_mock.get("/test-async").mock(
            return_value=HttpxResponse(200, json={"m": "ga"})
        )
        respx_mock.post("/test-post").mock(
            return_value=HttpxResponse(200, json={"m": "po"})
        )
        respx_mock.put("/test-put").mock(
            return_value=HttpxResponse(200, json={"m": "pu"})
        )
        respx_mock.delete("/test-delete").mock(
            return_value=HttpxResponse(200, json={"m": "d"})
        )
        respx_mock.patch("/test-patch").mock(
            return_value=HttpxResponse(200, json={"m": "pa"})
        )

        assert sync_client.get_test() == {"m": "g"}
        assert await async_client.get_test_async() == {"m": "ga"}
        assert sync_client.post_test() == {"m": "po"}
        assert sync_client.put_test() == {"m": "pu"}
        assert sync_client.delete_test() == {"m": "d"}
        assert sync_client.patch_test() == {"m": "pa"}

    sync_client.engine.close()
    await async_client.engine.aclose()


def test_httpx_engine_payload_types() -> None:
    from asas.core.models import Request
    from asas.engines.httpx import _prepare_httpx_request

    # Test with raw data
    req_data = Request(method="POST", url="http://h", payload=Payload(data=b"raw"))
    httpx_req = _prepare_httpx_request(req_data)
    assert httpx_req.content == b"raw"

    # Test with files
    req_files = Request(
        method="POST", url="http://h", payload=Payload(files={"f": b"c"})
    )
    httpx_req = _prepare_httpx_request(req_files)
    assert "multipart/form-data" in httpx_req.headers["content-type"]


def test_client_custom_engine() -> None:
    engine = HTTPXSyncEngine()
    client = AsasClient(base_url="https://api.example.com", engine=engine)
    assert client.engine is engine
    client.engine.close()
