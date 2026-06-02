import pytest
import respx
from httpx import Response as HttpxResponse

from asas import AsasAsyncClient, AsasClient, RefreshingBearerAuth, Response, get


class RefreshClient(AsasClient):
    @get("/protected")
    def get_protected(self, response: Response) -> bool:
        return response.status_code == 200


class AsyncRefreshClient(AsasAsyncClient):
    @get("/protected")
    async def get_protected(self, response: Response) -> bool:
        return response.status_code == 200


def test_sync_automatic_refresh() -> None:
    def refresh_cb() -> str:
        return "new-token"

    auth = RefreshingBearerAuth("old-token", refresh_callback=refresh_cb)
    client = RefreshClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # First call fails with 401
        route1 = respx_mock.get("/protected").mock(
            side_effect=[
                HttpxResponse(401),  # First call
                HttpxResponse(200),  # Second call (after refresh)
            ]
        )

        assert client.get_protected() is True
        assert route1.call_count == 2
        assert route1.calls[0].request.headers["Authorization"] == "Bearer old-token"
        assert route1.calls[1].request.headers["Authorization"] == "Bearer new-token"


@pytest.mark.asyncio
async def test_async_automatic_refresh() -> None:
    async def arefresh_cb() -> str:
        return "new-async-token"

    auth = RefreshingBearerAuth("old-token", async_refresh_callback=arefresh_cb)
    client = AsyncRefreshClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route1 = respx_mock.get("/protected").mock(
            side_effect=[
                HttpxResponse(401),
                HttpxResponse(200),
            ]
        )

        assert await client.get_protected() is True
        assert route1.call_count == 2
        assert route1.calls[0].request.headers["Authorization"] == "Bearer old-token"
        assert (
            route1.calls[1].request.headers["Authorization"] == "Bearer new-async-token"
        )
    await client.engine.aclose()


def test_refresh_limit() -> None:
    # Verify it only retries once
    def refresh_cb() -> str:
        return "still-old-token"

    auth = RefreshingBearerAuth("old-token", refresh_callback=refresh_cb)
    client = RefreshClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # Always return 401
        route1 = respx_mock.get("/protected").mock(return_value=HttpxResponse(401))

        # Should return the 401 response after one retry
        assert client.get_protected() is False
        assert route1.call_count == 2
