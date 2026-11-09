"""Automatic token refresh on a 401, shown against a mocked server (offline)."""

import asyncio
from typing import Any, Dict

import httpx
import respx

from asas import AsasAsyncClient, RefreshingBearerAuth, get


class ProtectedAsyncClient(AsasAsyncClient):
    @get("/me")
    async def get_profile(self) -> Dict[str, Any]:
        raise NotImplementedError


async def main() -> None:
    # 1. Define a callback to handle token refresh logic
    async def my_token_refresher() -> str:
        print("[Auth] Token expired! Refreshing...")
        # In a real app, you would make a call to your auth server here
        await asyncio.sleep(0.1)
        new_token = "fresh-secure-token-abc-123"
        print(f"[Auth] New token acquired: {new_token}")
        return new_token

    # 2. Initialize the client with RefreshingBearerAuth, starting from an
    #    'expired' token to trigger the refresh.
    auth = RefreshingBearerAuth(
        token="expired-token", async_refresh_callback=my_token_refresher
    )

    print("--- Automatic Token Refresh Example ---")
    async with ProtectedAsyncClient(
        base_url="https://api.example.com", auth=auth
    ) as client:
        print(f"Initial Token: {auth.token}")

        # 3. The first call gets a 401, so the client refreshes the token and
        #    retries the request exactly once.
        with respx.mock(base_url="https://api.example.com") as server:
            route = server.get("/me").mock(
                side_effect=[
                    httpx.Response(401),
                    httpx.Response(200, json={"name": "Ada"}),
                ]
            )
            print("\n[Client] Making request to protected endpoint...")
            profile = await client.get_profile()
            print(f"Profile: {profile}")
            for call in route.calls:
                print(f"  sent Authorization: {call.request.headers['Authorization']}")


if __name__ == "__main__":
    asyncio.run(main())
