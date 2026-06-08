import pytest
import respx
from httpx import Response as HttpxResponse

from asas import (
    APIKeyAuth,
    APIKeyLocation,
    AsasClient,
    BearerAuth,
    CompositeAuth,
    DigestAuth,
    NoAuth,
    OAuth2ClientCredentialsAuth,
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


def test_digest_auth_challenge_response() -> None:
    auth = DigestAuth("alice", "secret")
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    challenge = (
        'Digest realm="test@example.com", '
        'qop="auth", '
        'nonce="abc123nonce", '
        'opaque="opaque-value", '
        "algorithm=MD5"
    )

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        route = respx_mock.get("/protected").mock(
            side_effect=[
                HttpxResponse(401, headers={"WWW-Authenticate": challenge}),
                HttpxResponse(200),
            ]
        )

        result = client.get_protected()
        assert result.status_code == 200
        assert route.call_count == 2

        # First request carries no credentials.
        assert "Authorization" not in route.calls[0].request.headers

        # Second request carries a well-formed digest derived from the challenge.
        digest = route.calls[1].request.headers["Authorization"]
        assert digest.startswith("Digest ")
        assert 'username="alice"' in digest
        assert 'realm="test@example.com"' in digest
        assert 'nonce="abc123nonce"' in digest
        assert 'uri="/protected"' in digest
        assert "qop=auth" in digest
        assert "nc=00000001" in digest
        assert "cnonce=" in digest
        assert 'opaque="opaque-value"' in digest
        assert 'response="' in digest


def test_digest_auth_ignores_non_digest_challenge() -> None:
    auth = DigestAuth("alice", "secret")
    assert (
        auth.handle_challenge(
            Response(401, {"WWW-Authenticate": 'Basic realm="x"'}, b"", "")
        )
        is False
    )


def test_oauth2_client_credentials_fetches_token() -> None:
    calls = []

    def fetch(form: dict) -> dict:
        calls.append(form)
        return {"access_token": "minted-token", "expires_in": 3600}

    auth = OAuth2ClientCredentialsAuth(
        token_url="https://auth.example.com/token",
        client_id="id",
        client_secret="secret",
        scope="read",
        token_fetcher=fetch,
    )
    client = AuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # First call 401 (no token yet) triggers a fetch + retry.
        route = respx_mock.get("/protected").mock(
            side_effect=[HttpxResponse(401), HttpxResponse(200)]
        )

        client.get_protected()
        assert route.call_count == 2
        assert route.calls[1].request.headers["Authorization"] == "Bearer minted-token"
        assert calls[0]["grant_type"] == "client_credentials"
        assert calls[0]["scope"] == "read"
        assert auth.is_expired is False


@pytest.mark.asyncio
async def test_oauth2_client_credentials_async_fetch() -> None:
    from asas import AsasAsyncClient

    async def fetch(form: dict) -> str:
        return "async-token"

    class AsyncAuthClient(AsasAsyncClient):
        @get("/protected")
        async def get_protected(self, response: Response) -> Response:
            return response

    auth = OAuth2ClientCredentialsAuth(
        token_url="https://auth.example.com/token",
        client_id="id",
        client_secret="secret",
        async_token_fetcher=fetch,
    )
    client = AsyncAuthClient(base_url="https://api.example.com", auth=auth)

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/protected").mock(
            side_effect=[HttpxResponse(401), HttpxResponse(200)]
        )

        response = await client.get_protected()
        assert response.status_code == 200
        assert auth.token == "async-token"
    await client.engine.aclose()
