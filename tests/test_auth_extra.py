import pytest
import respx
from httpx import Response as HttpxResponse

from asas import (
    APIKeyAuth,
    APIKeyLocation,
    AsasClient,
    BearerAuth,
    CompositeAuth,
    NoAuth,
    Response,
    get,
)


class AuthClient(AsasClient):
    @get("/protected")
    def get_protected(self, response: Response) -> Response:
        return response


def test_no_auth_adds_nothing() -> None:
    client = AuthClient(base_url="https://api.example.com", auth=NoAuth())

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        client.get_protected()
        assert route.called
        assert "Authorization" not in route.calls.last.request.headers


def test_api_key_cookie_auth() -> None:
    auth = APIKeyAuth("secret-key", name="session", location=APIKeyLocation.COOKIE)
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        client.get_protected()
        assert route.calls.last.request.headers["Cookie"] == "session=secret-key"


def test_composite_auth_applies_all_strategies() -> None:
    auth = CompositeAuth(
        BearerAuth("token-abc"),
        APIKeyAuth("key-123", name="X-API-Key"),
    )
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        client.get_protected()
        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer token-abc"
        assert request.headers["X-API-Key"] == "key-123"


def test_composite_auth_refreshes_refreshable_members() -> None:
    from asas import RefreshingBearerAuth

    refreshing = RefreshingBearerAuth("old", refresh_callback=lambda: "new")
    auth = CompositeAuth(APIKeyAuth("key-123"), refreshing)
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(
            side_effect=[HttpxResponse(401), HttpxResponse(200)]
        )

        client.get_protected()
        assert route.call_count == 2
        assert route.calls[0].request.headers["Authorization"] == "Bearer old"
        assert route.calls[1].request.headers["Authorization"] == "Bearer new"
