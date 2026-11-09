"""A sync and an async client against the public DummyJSON API (needs network)."""

import asyncio
from typing import List

from pydantic import BaseModel

from asas import AsasAsyncClient, AsasClient, get


class Product(BaseModel):
    id: int
    title: str
    description: str
    price: float


class ProductList(BaseModel):
    products: List[Product]
    total: int


class DummyJSONClient(AsasClient):
    """Synchronous client example."""

    def __init__(self) -> None:
        super().__init__(base_url="https://dummyjson.com")

    @get("/products")
    def get_products(self) -> ProductList:
        """The return annotation is the parsed type."""

    @get("/products/search")
    def search_products(self, q: str) -> ProductList:
        """``q`` is not in the path, so it becomes a query parameter."""


class AsyncDummyJSONClient(AsasAsyncClient):
    """Asynchronous client example."""

    def __init__(self) -> None:
        super().__init__(base_url="https://dummyjson.com")

    @get("/products/{id}")
    async def get_product_async(self, id: int) -> Product:
        """``id`` fills the ``{id}`` placeholder in the path."""


async def main() -> None:
    print("--- DummyJSON Example ---")

    with DummyJSONClient() as sync_client:
        try:
            print("\n[Sync] Fetching all products...")
            page = sync_client.get_products()
            print(f"Found {len(page.products)} of {page.total} products.")
            print(
                f"First product: {page.products[0].title} (${page.products[0].price})"
            )

            print("\n[Sync] Searching for 'phone'...")
            print(f"Matches: {sync_client.search_products(q='phone').total}")
        except Exception as e:
            print(f"Sync request failed: {e}")

    async with AsyncDummyJSONClient() as async_client:
        try:
            print("\n[Async] Fetching product ID 1...")
            product = await async_client.get_product_async(id=1)
            print(f"Product title: {product.title}")
            print(f"Description: {product.description[:50]}...")
        except Exception as e:
            print(f"Async request failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
