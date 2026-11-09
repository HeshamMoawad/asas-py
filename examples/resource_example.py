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

from typing import Annotated, Any, List

from pydantic import BaseModel

from asas import AsasClient, AsasResource, Body, OffsetPaginator, get, post, put

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


# A resource = a base path + a model (via the generic) + an optional paginator.
class Products(AsasResource[Product]):
    path = "/products"
    # DummyJSON paginates with ?skip=&limit= and wraps items under "products".
    paginator = OffsetPaginator(
        offset_param="skip", limit_param="limit", limit=10, items_key="products"
    )

    # DummyJSON's simulated create lives at /products/add, not /products.
    # Overriding a CRUD verb with a plain endpoint keeps the same signature.
    @post("/products/add")
    def create(self, obj: Product) -> Product:
        ...

    # DummyJSON rejects an ``id`` in a PUT body: exclude_unset leaves out any
    # field the caller did not set (so ``Product(title=...)`` sends no id).
    @put("/products/{id}")
    def update(
        self, id: Any, obj: Annotated[Product, Body(exclude_unset=True)]
    ) -> Product:
        ...

    # Custom endpoints live right next to the generated CRUD.
    @get("/products/search")
    def search(self, q: str) -> ProductPage:
        ...


class Users(AsasResource[User]):
    path = "/users"

    # Nested custom endpoint: the posts written by a given user.
    @get("/users/{id}/posts")
    def posts(self, id: int) -> PostPage:
        ...


class DummyJSONClient(AsasClient):
    products = Products()
    users = Users()


def main() -> None:
    with DummyJSONClient(base_url=BASE_URL) as client:
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

            client.products.delete(1)
            print("[DELETE] /products/1 -> ok (non-2xx would raise)")

            # --- Single page (no loop code) ------------------------------------
            first_page = client.products.list(limit=3)
            print(f"[LIST]   /products?limit=3 -> {len(first_page)} products returned")

            # --- Custom endpoint -----------------------------------------------
            matches = client.products.search(q="phone").products
            print(f"[SEARCH] /products/search?q=phone -> {len(matches)} matches")

            # --- Lazy pagination: iterate, fetch pages on demand ----------------
            print("[LAZY]   iterating /products (limit=10 per request)...")
            for product in client.products:
                print(f"         - {product.title}")
            # The loop fetches pages automatically and stops when a page is short.

            # --- Nested custom endpoint on another resource ----------------------
            posts = client.users.posts(id=1).posts
            print(f"[NESTED] /users/1/posts -> {len(posts)} posts by user 1")
            if posts:
                print(f"         first post title: {posts[0].title!r}")

        except Exception as exc:  # keep the example friendly offline
            print(f"(network error — is dummyjson.com reachable?): {exc}")


if __name__ == "__main__":
    main()
