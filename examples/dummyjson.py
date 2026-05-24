import asyncio
from typing import Any, Dict, List, cast

from asas import AsasClient, Response, get, post


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
        """
        Search for products.
        Note: Currently q must be handled manually or via a more advanced
        request builder we will implement later.
        """
        data = cast(Dict[str, Any], response.json())
        return cast(List[Dict[str, Any]], data.get("products", []))

    @get("/products/{id}")
    async def get_product_async(self, response: Response, id: int) -> Dict[str, Any]:
        """Get a single product asynchronously."""
        return cast(Dict[str, Any], response.json())

    @post("/auth/login")
    async def login(self, response: Response) -> Dict[str, Any]:
        """Login example."""
        return cast(Dict[str, Any], response.json())


async def main() -> None:
    client = DummyJSONClient()

    print("--- DummyJSON Example ---")

    # Sync: Get products
    try:
        print("\n[Sync] Fetching all products...")
        products = client.get_products()
        if products:
            print(f"Found {len(products)} products.")
            print(f"First product: {products[0].get('title')}")
    except Exception as e:
        print(f"Sync request failed: {e} (Expected if no internet access)")

    # Async: Get specific product
    try:
        print("\n[Async] Fetching product ID 1...")
        product = await client.get_product_async(id=1)
        print(product)
        print(f"Product title: {product.get('title')}")
    except Exception as e:
        print(f"Async request failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
