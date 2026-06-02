import asyncio
from typing import Any, Dict, List, cast

from asas import AsasAsyncClient, AsasClient, Response, get, post


class DummyJSONClient(AsasClient):
    def __init__(self) -> None:
        super().__init__(base_url="https://dummyjson.com")

    @get("/products")
    def get_products(self, response: Response) -> List[Dict[str, Any]]:
        """Get all products synchronously."""
        data = cast(Dict[str, Any], response.json())
        return cast(List[Dict[str, Any]], data.get("products", []))

    @get("/products/search")
    def search_products(self, response: Response, q: str) -> List[Dict[str, Any]]:
        """Search for products."""
        data = cast(Dict[str, Any], response.json())
        return cast(List[Dict[str, Any]], data.get("products", []))


class AsyncDummyJSONClient(AsasAsyncClient):
    def __init__(self) -> None:
        super().__init__(base_url="https://dummyjson.com")

    @get("/products/{id}")
    async def get_product_async(self, response: Response, id: int) -> Dict[str, Any]:
        """Get a single product asynchronously."""
        return cast(Dict[str, Any], response.json())

    @post("/auth/login")
    async def login(self, response: Response) -> Dict[str, Any]:
        """Login example."""
        return cast(Dict[str, Any], response.json())


async def main() -> None:
    sync_client = DummyJSONClient()
    async_client = AsyncDummyJSONClient()

    print("--- DummyJSON Example ---")

    # Sync: Get products
    try:
        print("\n[Sync] Fetching all products...")
        products = sync_client.get_products()
        if products:
            print(f"Found {len(products)} products.")
            print(f"First product: {products[0].get('title')}")
    except Exception as e:
        print(f"Sync request failed: {e}")

    # Async: Get specific product
    try:
        print("\n[Async] Fetching product ID 1...")
        product = await async_client.get_product_async(id=1)
        print(f"Product title: {product.get('title')}")
    except Exception as e:
        print(f"Async request failed: {e}")

    sync_client.engine.close()
    await async_client.engine.aclose()


if __name__ == "__main__":
    asyncio.run(main())
