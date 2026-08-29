import asyncio
from typing import Any, Dict

from asas import AsasAsyncClient, RefreshingBearerAuth, Response, get


class ProtectedAsyncClient(AsasAsyncClient):
    @get("/me")
    async def get_profile(self, response: Response) -> Dict[str, Any]:
        return response.json()  # type: ignore[no-any-return]


async def main() -> None:
    # 1. Define a callback to handle token refresh logic
    async def my_token_refresher() -> str:
        print("[Auth] Token expired! Refreshing...")
        # In a real app, you would make a call to your auth server here
        await asyncio.sleep(0.5)
        new_token = "fresh-secure-token-abc-123"
        print(f"[Auth] New token acquired: {new_token}")
        return new_token

    # 2. Initialize the client with RefreshingBearerAuth
    # We start with an 'expired' token to trigger the refresh
    auth = RefreshingBearerAuth(
        token="expired-token", async_refresh_callback=my_token_refresher
    )

    client = ProtectedAsyncClient(base_url="https://api.example.com", auth=auth)

    print("--- Automatic Token Refresh Example ---")
    if isinstance(client.auth, RefreshingBearerAuth):
        print(f"Initial Token: {client.auth.token}")

    # 3. When you call a protected endpoint:
    # If the server returns 401, the client will:
    #   a. Call my_token_refresher()
    #   b. Update its internal token
    #   c. Retry the request automatically
    try:
        # Note: This will only actually 'refresh' if we were hitting a real server
        # that returned 401. This example shows the code structure.
        print("\n[Client] Making request to protected endpoint...")
        # profile = await client.get_profile()
    except Exception as e:
        print(f"Request failed: {e}")

    await client.engine.aclose()


if __name__ == "__main__":
    asyncio.run(main())
