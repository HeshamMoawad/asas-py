"""Resources: convention-driven CRUD plus lazy, no-loop-code pagination.

This example is **live**: it talks to the public DummyJSON REST API
(``https://dummyjson.com``), which offers Products and Users resources with
real ``?limit=&skip=`` pagination and simulated writes. Run it as-is:

    python examples/resource_example.py

DummyJSON requires a small tailor-up: its ``POST /products/add`` and
``?limit=&skip=`` shapes differ from the framework defaults, so this example
shows how a resource customises both the CRUD verbs and its paginator.
The :meth:`create` verb is overridden to hit ``/add``, and :class:`OffsetPaginator`
is configured to use DummyJSON's ``skip``/``limit`` params.
"""

from typing import List

from pydantic import BaseModel

from asas import AsasClient, AsasResource, OffsetPaginator, Response, get
from asas.decorators import execute_sync

BASE_URL = "https://dummyjson.com"


class Product(BaseModel):
    id: int = 0
    title: str = ""
    price: float = 0.0
    category: str = ""
    brand: str = ""


class ProductPage(BaseModel):
    """DummyJSON wraps list items under a keyword, e.g. ``{"products": [...]}``."""

    products: List[Product]


class User(BaseModel):
    id: int = 0
    firstName: str = ""
    lastName: str = ""
    email: str = ""


class PostSummary(BaseModel):
    id: int
    title: str


class PostPage(BaseModel):
    """``/users/{id}/posts`` also wraps items under a ``posts`` keyword."""

    posts: List[PostSummary]


# A resource = a base path + an optional model + an optional paginator.
class Products(AsasResource):
    path = "/products"
    model = Product
    # DummyJSON paginates with ?skip=&limit= and wraps items under "products".
    paginator = OffsetPaginator(
        offset_param="skip", limit_param="limit", limit=10, items_key="products"
    )

    # DummyJSON's simulated create lives at /products/add, not /products.
    def create(self, obj: Product) -> Product:
        response = execute_sync(
            self, lambda: self._build("POST", "/products/add", body=obj)
        )
        return self._parse_one(response)  # type: ignore[no-any-return]

    # DummyJSON rejects an ``id`` in a PUT body, so exclude it before sending.
    def update(self, id: int, obj: Product) -> Product:
        body = obj.model_dump(exclude={"id"})
        response = execute_sync(
            self, lambda: self._build("PUT", f"/products/{id}", body=body)
        )
        return self._parse_one(response)  # type: ignore[no-any-return]

    # Custom endpoints live right next to the generated CRUD.
    @get("/products/search", response_model=ProductPage)
    def search(self, page: ProductPage, q: str) -> List[Product]:
        return page.products


class Users(AsasResource):
    path = "/users"
    model = User

    # Nested custom endpoint: the posts written by a given user.
    @get("/users/{id}/posts", response_model=PostPage)
    def posts(self, page: PostPage, id: int) -> List[PostSummary]:
        return page.posts


class DummyJSONClient(AsasClient):
    products = Products()
    users = Users()


def main() -> None:
    client = DummyJSONClient(base_url=BASE_URL)
    try:
        # --- Generated CRUD -------------------------------------------------
        product = client.products.get(1)
        print(f"[GET]    /products/1 -> {product.title} (${product.price})")

        # DummyJSON simulates writes; they don't persist. Create returns a new id.
        created = client.products.create(Product(title="Test Widget", price=12.99))
        print(f"[POST]   /products/add -> created id={created.id}")

        # Update a real product: PUT merges the fields we send and returns it.
        updated = client.products.update(
            1, Product(title="Essence Mascara", price=25.0)
        )
        print(f"[PUT]    /products/1 -> price now ${updated.price}")

        delete_response: Response = client.products.delete(1)
        print(f"[DELETE] /products/1 -> HTTP {delete_response.status_code}")

        # --- Single page (no loop code) ------------------------------------
        first_page = client.products.list(limit=3)
        print(f"[LIST]   /products?limit=3 -> {len(first_page)} products returned")

        # --- Custom endpoint -----------------------------------------------
        matches = client.products.search(q="phone")
        print(f"[SEARCH] /products/search?q=phone -> {len(matches)} matches")

        # --- Lazy pagination: iterate, fetch pages on demand ----------------
        print("[LAZY]   iterating /products (limit=10 per request)...")
        for product in client.products:
            print(f"         - {product.title}")
        # The loop fetches pages automatically and stops when a page is short.

        # --- Nested custom endpoint on another resource ----------------------
        posts = client.users.posts(id=1)
        print(f"[NESTED] /users/1/posts -> {len(posts)} posts by user 1")
        if posts:
            print(f"         first post title: {posts[0].title!r}")

    except Exception as exc:  # keep the example friendly offline
        print(f"(network error — is dummyjson.com reachable?): {exc}")
    finally:
        client.engine.close()


if __name__ == "__main__":
    main()
