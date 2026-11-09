import pytest
import respx
from httpx import Response as HttpxResponse

from asas import (
    APIKeyAuth,
    APIKeyLocation,
    AsasClient,
    BasicAuth,
    BearerAuth,
    Request,
    Response,
    get,
)


class AuthClient(AsasClient):
    @get("/protected")
    def get_protected(self) -> Response:
        raise NotImplementedError


def test_basic_auth() -> None:
    auth = BasicAuth("user", "pass")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # Basic user:pass is dXNlcjpwYXNz
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        assert client.get_protected().status_code == 200
        assert route.called
        assert route.calls.last.request.headers["Authorization"] == "Basic dXNlcjpwYXNz"


def test_bearer_auth() -> None:
    auth = BearerAuth("mytoken")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        assert client.get_protected().status_code == 200
        assert route.called
        assert route.calls.last.request.headers["Authorization"] == "Bearer mytoken"


def test_api_key_header_auth() -> None:
    auth = APIKeyAuth("secret-key", name="X-Custom-Key")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))

        assert client.get_protected().status_code == 200
        assert route.called
        assert route.calls.last.request.headers["X-Custom-Key"] == "secret-key"


def test_api_key_query_auth() -> None:
    auth = APIKeyAuth("secret-key", name="api_key", location=APIKeyLocation.QUERY)
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # respx matches with query params
        route = respx_mock.get("/protected?api_key=secret-key").mock(
            return_value=HttpxResponse(200)
        )

        assert client.get_protected().status_code == 200
        assert route.called


def test_api_key_location_accepts_string() -> None:
    # Backwards compatible: plain strings are coerced to the enum.
    auth = APIKeyAuth("secret-key", location="query")
    assert auth.location is APIKeyLocation.QUERY

    with pytest.raises(ValueError):
        APIKeyAuth("secret-key", location="body")


def test_runtime_auth_update() -> None:
    client = AuthClient(base_url="https://api.example.com")

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # 1. No auth initially
        route1 = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))
        assert client.get_protected().status_code == 200
        assert "Authorization" not in route1.calls.last.request.headers

        # 2. Update auth via setter
        from asas import BearerAuth

        client.auth = BearerAuth("new-token")

        route2 = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))
        assert client.get_protected().status_code == 200
        assert route2.calls.last.request.headers["Authorization"] == "Bearer new-token"

        # 3. Clear auth via setter
        client.auth = None
        route3 = respx_mock.get("/protected").mock(return_value=HttpxResponse(200))
        assert client.get_protected().status_code == 200
        assert "Authorization" not in route3.calls.last.request.headers


def test_api_key_cookie_goes_to_request_cookies() -> None:
    request = Request("GET", "https://api.example.com/x")
    APIKeyAuth("k", name="session", location=APIKeyLocation.COOKIE).apply(request)
    APIKeyAuth("t", name="trace", location=APIKeyLocation.COOKIE).apply(request)
    assert request.cookies == {"session": "k", "trace": "t"}
    assert "Cookie" not in request.headers
