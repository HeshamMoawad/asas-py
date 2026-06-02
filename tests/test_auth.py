import pytest
import respx
from httpx import Response as HttpxResponse

from asas import APIKeyAuth, AsasClient, BasicAuth, BearerAuth, Response, get


class AuthClient(AsasClient):
    @get("/protected")
    def get_protected(self, response: Response) -> bool:
        return response.status_code == 200


def test_basic_auth() -> None:
    auth = BasicAuth("user", "pass")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # Basic user:pass is dXNlcjpwYXNz
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        assert client.get_protected() is True
        assert route.called
        assert route.calls.last.request.headers["Authorization"] == "Basic dXNlcjpwYXNz"


def test_bearer_auth() -> None:
    auth = BearerAuth("mytoken")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        assert client.get_protected() is True
        assert route.called
        assert route.calls.last.request.headers["Authorization"] == "Bearer mytoken"


def test_api_key_header_auth() -> None:
    auth = APIKeyAuth("secret-key", name="X-Custom-Key")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        assert client.get_protected() is True
        assert route.called
        assert route.calls.last.request.headers["X-Custom-Key"] == "secret-key"


def test_api_key_query_auth() -> None:
    auth = APIKeyAuth("secret-key", name="api_key", location="query")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # respx matches with query params
        route = respx_mock.get("/protected?api_key=secret-key").mock(
            return_value=HttpxResponse(200)
        )

        assert client.get_protected() is True
        assert route.called
