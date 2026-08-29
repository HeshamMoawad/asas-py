import asyncio
from typing import List

from pydantic import BaseModel

from asas import AsasAsyncClient, AsasClient, Response, get


# Define Pydantic models for better type safety
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

    @get("/products", response_model=ProductList)
    def get_products(self, data: ProductList) -> List[Product]:
        """Get all products synchronously with Pydantic parsing."""
        return data.products

    @get("/products/search", response_model=ProductList)
    def search_products(self, data: ProductList, q: str) -> List[Product]:
        """Search for products using query parameters."""
        return data.products


class AsyncDummyJSONClient(AsasAsyncClient):
    """Asynchronous client example."""

    def __init__(self) -> None:
        super().__init__(base_url="https://dummyjson.com")

    @get("/products/{id}", response_model=Product)
    async def get_product_async(self, product: Product, id: int) -> Product:
        """Get a single product asynchronously."""
        return product


async def main() -> None:
    sync_client = DummyJSONClient()
    async_client = AsyncDummyJSONClient()

    print("--- DummyJSON Enhanced Example ---")

    # Sync: Get products
    try:
        print("\n[Sync] Fetching all products...")
        products = sync_client.get_products()
        if products:
            print(f"Found {len(products)} products.")
            print(f"First product: {products[0].title} (${products[0].price})")
    except Exception as e:
        print(f"Sync request failed: {e}")

    # Async: Get specific product
    try:
        print("\n[Async] Fetching product ID 1...")
        product = await async_client.get_product_async(id=1)
        print(f"Product title: {product.title}")
        print(f"Description: {product.description[:50]}...")
    except Exception as e:
        print(f"Async request failed: {e}")

    sync_client.engine.close()
    await async_client.engine.aclose()


if __name__ == "__main__":
    asyncio.run(main())
