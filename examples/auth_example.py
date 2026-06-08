"""Showcase of every authentication strategy shipped with Asas.

The clients here are only constructed (no live calls) so the example runs
offline; each block shows how a given auth scheme is wired into a client.
"""

from typing import Any, Dict

from asas import (
    APIKeyAuth,
    APIKeyLocation,
    AsasClient,
    BasicAuth,
    BearerAuth,
    CompositeAuth,
    DigestAuth,
    NoAuth,
    OAuth2ClientCredentialsAuth,
    RefreshingBearerAuth,
    Response,
    get,
)


class ProtectedClient(AsasClient):
    @get("/protected")
    def get_data(self, response: Response) -> Dict[str, Any]:
        return response.json()  # type: ignore[no-any-return]


def main() -> None:
    base = "https://api.example.com"

    # 1. No authentication (explicit, readable alternative to ``auth=None``).
    print(NoAuth().__class__.__name__)

    # 2. HTTP Basic.
    ProtectedClient(base_url=base, auth=BasicAuth("username", "password"))

    # 3. Bearer token.
    ProtectedClient(base_url=base, auth=BearerAuth("your-secret-token"))

    # 4. API key — in a header, query string, or cookie.
    ProtectedClient(base_url=base, auth=APIKeyAuth("key", name="X-API-Key"))
    ProtectedClient(
        base_url=base,
        auth=APIKeyAuth("key", name="api_key", location=APIKeyLocation.QUERY),
    )
    ProtectedClient(
        base_url=base,
        auth=APIKeyAuth("key", name="session", location=APIKeyLocation.COOKIE),
    )

    # 5. Bearer token with automatic refresh on 401.
    ProtectedClient(
        base_url=base,
        auth=RefreshingBearerAuth("token", refresh_callback=lambda: "fresh-token"),
    )

    # 6. OAuth2 client-credentials grant (token minted lazily, refreshed on 401).
    ProtectedClient(
        base_url=base,
        auth=OAuth2ClientCredentialsAuth(
            token_url="https://auth.example.com/oauth/token",
            client_id="my-client-id",
            client_secret="my-client-secret",
            scope="read write",
        ),
    )

    # 7. HTTP Digest (challenge/response handled automatically).
    ProtectedClient(base_url=base, auth=DigestAuth("username", "password"))

    # 8. Composite — combine several schemes on one request.
    ProtectedClient(
        base_url=base,
        auth=CompositeAuth(
            APIKeyAuth("key", name="X-API-Key"),
            BearerAuth("your-secret-token"),
        ),
    )

    print("Configured clients for all auth strategies.")


if __name__ == "__main__":
    main()
