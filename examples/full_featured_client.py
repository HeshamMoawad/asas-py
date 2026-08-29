import asyncio
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from asas import (
    APIKeyAuth,
    APIKeyLocation,
    AsasAsyncClient,
    AsasClient,
    BasicAuth,
    BearerAuth,
    RefreshingBearerAuth,
    Response,
    get,
    post,
)


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


# --- 2. Synchronous Client with Multiple Auth & use_auth ---
class SyncStoreClient(AsasClient):
    """
    Demonstrates:
    - Sync client
    - Disabling auth for specific endpoints
    - Pydantic integration
    """

    def __init__(self, base_url: str, auth: Optional[Any] = None):
        super().__init__(base_url=base_url, auth=auth)

    @get("/products", response_model=List[Product], use_auth=False)
    def get_public_products(self, products: List[Product]) -> List[Product]:
        """A public endpoint that doesn't require authentication."""
        return products

    @get("/user/orders")
    def get_my_orders(self, response: Response) -> List[Dict[str, Any]]:
        """A protected endpoint that uses the client's auth."""
        return response.json().get("orders", [])  # type: ignore[no-any-return]

    @post("/auth/login", response_model=AuthResponse, use_auth=False)
    def login(self, auth_data: AuthResponse, credentials: Credentials) -> AuthResponse:
        """Login to get a token.

        `credentials` is a Pydantic model, so it is sent as the JSON body.
        A plain ``dict`` here would instead be routed to the query string.
        """
        return auth_data


# --- 3. Asynchronous Client with Automatic Refresh ---
class AsyncStoreClient(AsasAsyncClient):
    """
    Demonstrates:
    - Async client
    - Automatic token refresh
    """

    @get("/products/{id}", response_model=Product)
    async def get_product(self, product: Product, id: int) -> Product:
        return product


async def run_async_example() -> None:
    print("\n--- Async Example with Automatic Refresh ---")

    # This callback would typically call an API to get a new token
    async def refresh_token_callback() -> str:
        print("[Auth] Refreshing token...")
        await asyncio.sleep(0.1)  # Simulate network
        return "new-refreshed-async-token"

    auth = RefreshingBearerAuth(
        token="expired-token", async_refresh_callback=refresh_token_callback
    )

    # Note: In a real scenario, the first call to a protected endpoint
    # might return 401, triggering the refresh_token_callback.
    async_client = AsyncStoreClient(base_url="https://api.example.com", auth=auth)

    if isinstance(async_client.auth, RefreshingBearerAuth):
        print(f"Initial Token: {async_client.auth.token}")

    # Simulate a call (this would trigger refresh if the server returned 401)
    # Since we can't easily mock a real server here without respx,
    # we just show the setup.

    await async_client.engine.aclose()


def main() -> None:
    # --- Sync Example ---
    print("--- Sync Example ---")

    # 1. Initialize with Basic Auth
    basic_auth = BasicAuth("admin", "secret123")
    client = SyncStoreClient(base_url="https://api.example.com", auth=basic_auth)
    print(f"Using auth: {type(client.auth).__name__}")

    # 2. Change Auth at runtime (e.g., after a manual login)
    print("Updating auth to Bearer token...")
    client.auth = BearerAuth("manual-token-xyz")
    print(f"New auth: {type(client.auth).__name__}")

    # 3. API Key Auth Example
    print("Updating auth to API Key...")
    client.auth = APIKeyAuth(
        "my-api-key-123", name="X-Store-Key", location=APIKeyLocation.HEADER
    )

    # 4. Building a request body: a Pydantic model is sent as JSON.
    #    A call like client.login(credentials=creds) would POST this as the body.
    creds = Credentials(username="admin", password="secret123")
    print(f"Prepared login body for user: {creds.username}")

    # Clean up sync client
    client.engine.close()

    # --- Async Example ---
    asyncio.run(run_async_example())


if __name__ == "__main__":
    main()
