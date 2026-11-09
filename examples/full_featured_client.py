"""The v0.2 showcase: models, markers, auth, hooks, errors and a ``with`` block.

Everything runs offline: respx stands in for ``https://api.example.com``.
"""

import asyncio
from typing import Annotated, Any, Dict, List, Optional

import httpx
import respx
from pydantic import BaseModel

from asas import (
    APIKeyAuth,
    APIKeyLocation,
    AsasAsyncClient,
    AsasClient,
    BasicAuth,
    BearerAuth,
    Header,
    Hooks,
    NotFoundError,
    Query,
    RefreshingBearerAuth,
    Request,
    get,
    post,
)

BASE_URL = "https://api.example.com"


# --- 1. Pydantic Models ---
class Product(BaseModel):
    id: int
    title: str
    price: float


class AuthResponse(BaseModel):
    token: str
    username: str


class Credentials(BaseModel):
    username: str
    password: str


def log_request(request: Request) -> None:
    """A client-level ``on_request`` hook: runs for every call the client makes."""
    print(f"  [hook] {request.method} {request.url} params={request.params}")


# --- 2. Synchronous client: markers, per-endpoint auth, typed returns ---
class SyncStoreClient(AsasClient):
    """
    Demonstrates:
    - The return annotation drives parsing; the body is never run
    - ``Query(alias=...)`` and ``Header`` markers
    - Disabling auth for specific endpoints
    - A Pydantic model parameter sent as the JSON body
    """

    @get("/products", use_auth=False)
    def get_public_products(
        self,
        search: Annotated[Optional[str], Query(alias="q")] = None,
        x_request_id: Annotated[Optional[str], Header()] = None,
    ) -> List[Product]:
        """``search`` goes out as ``?q=...``; ``x_request_id`` as ``X-Request-Id``."""

    @get("/products/{id}")
    def get_product(self, id: int) -> Product:
        """``id`` matches the ``{id}`` placeholder, so it is a path parameter."""

    @get("/user/orders")
    def get_my_orders(self) -> Dict[str, Any]:
        """A protected endpoint that uses the client's auth."""

    @post("/auth/login", use_auth=False)
    def login(self, credentials: Credentials) -> AuthResponse:
        """``credentials`` is a Pydantic model, so it is sent as the JSON body."""


# --- 3. Asynchronous client with automatic refresh ---
class AsyncStoreClient(AsasAsyncClient):
    @get("/products/{id}")
    async def get_product(self, id: int) -> Product:
        ...


def mock_store(server: respx.MockRouter) -> None:
    server.get("/products", params={"q": "mug"}).mock(
        return_value=httpx.Response(200, json=[{"id": 1, "title": "Mug", "price": 9.5}])
    )
    server.get("/products/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "title": "Mug", "price": 9.5})
    )
    server.get("/products/999").mock(
        return_value=httpx.Response(404, json={"error": "no such product"})
    )
    server.get("/user/orders").mock(
        return_value=httpx.Response(200, json={"orders": [{"id": 7}]})
    )
    server.post("/auth/login").mock(
        return_value=httpx.Response(200, json={"token": "t-123", "username": "admin"})
    )


async def run_async_example() -> None:
    print("\n--- Async Example with Automatic Refresh ---")

    async def refresh_token_callback() -> str:
        print("  [auth] Refreshing token...")
        await asyncio.sleep(0.05)  # simulate a network call
        return "new-refreshed-async-token"

    auth = RefreshingBearerAuth(
        token="expired-token", async_refresh_callback=refresh_token_callback
    )

    async with AsyncStoreClient(base_url=BASE_URL, auth=auth) as client:
        with respx.mock(base_url=BASE_URL) as server:
            server.get("/products/1").mock(
                side_effect=[
                    httpx.Response(401),
                    httpx.Response(200, json={"id": 1, "title": "Mug", "price": 9.5}),
                ]
            )
            product = await client.get_product(id=1)
            print(f"Got {product.title} after the token was refreshed: {auth.token}")


def main() -> None:
    print("--- Sync Example ---")

    # A client-level logger and a ``with`` block that closes the engine for us.
    hooks = Hooks(on_request=[log_request])
    with (
        SyncStoreClient(
            base_url=BASE_URL, auth=BasicAuth("admin", "secret123"), hooks=hooks
        ) as client,
        respx.mock(base_url=BASE_URL) as server,
    ):
        mock_store(server)

        print(f"Using auth: {type(client.auth).__name__}")

        # Markers: ?q=mug and an X-Request-Id header.
        products = client.get_public_products(search="mug", x_request_id="abc-1")
        print(f"Search returned {len(products)} product(s): {products[0].title}")

        print(f"Product 1: {client.get_product(id=1).title}")

        # Typed errors: a 404 raises NotFoundError instead of a parse error.
        try:
            client.get_product(id=999)
        except NotFoundError as exc:
            print(f"Caught NotFoundError (status {exc.status_code})")

        # Change auth at runtime (e.g. after a login).
        login = client.login(Credentials(username="admin", password="secret123"))
        client.auth = BearerAuth(login.token)
        print(
            f"Logged in as {login.username}; auth is now {type(client.auth).__name__}"
        )
        print(f"Orders: {client.get_my_orders()['orders']}")

        client.auth = APIKeyAuth(
            "my-api-key-123", name="X-Store-Key", location=APIKeyLocation.HEADER
        )
        print(f"Switched auth to {type(client.auth).__name__}")

    asyncio.run(run_async_example())


if __name__ == "__main__":
    main()
