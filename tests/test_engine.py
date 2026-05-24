import pytest
import respx
from httpx import Response as HttpxResponse

from asas.core.models import Request
from asas.engines.httpx import HTTPXEngine


@pytest.mark.asyncio
async def test_httpx_engine_async() -> None:
    engine = HTTPXEngine()
    async with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/test").mock(
            return_value=HttpxResponse(200, json={"message": "async-success"})
        )

        request = Request(method="GET", url="https://api.example.com/test")
        response = await engine.asend(request)

        assert response.status_code == 200
        assert response.json() == {"message": "async-success"}
    await engine.aclose()


def test_httpx_engine_sync() -> None:
    engine = HTTPXEngine()
    with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/test").mock(
            return_value=HttpxResponse(200, json={"message": "sync-success"})
        )

        request = Request(method="GET", url="https://api.example.com/test")
        response = engine.send(request)

        assert response.status_code == 200
        assert response.json() == {"message": "sync-success"}
    engine.close()
