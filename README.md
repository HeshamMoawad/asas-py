
<p align="center">
  <a href="https://asas.dev"><img src="https://heshammoawad.github.io/asas-py/assets/logo-without-bg.png" alt="Asas"></a>
</p>

<p align="center">
    <em>Asas framework, high performance, easy to learn, fast to code, ready for production</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/asas-py/"><img src="https://img.shields.io/pypi/v/asas-py" alt="PyPI version"></a>
  <a href="https://pypi.org/project/asas-py/"><img src="https://img.shields.io/pypi/pyversions/asas-py" alt="Python versions"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
</p>

---

> **Asas** is a Python framework for building **typed, simple API clients** in a few lines.
> You write a subclass, annotate methods with `@get`/`@post`/…, and Asas handles request
> building, parameter routing, Pydantic validation, authentication, refresh-and-retry, and
> paging for you — for synchronous **and** asynchronous code with the same decorators.

## Why Asas?

Traditional HTTP clients bury your API's shape in a pile of `requests.get(...)` calls, string
URLs, and manual JSON wrangling. Asas flips that: **your client class *is* your API client**,
declared once and typed end-to-end.

- Write your whole API client as a class with decorators — no boilerplate to maintain.
- One signature drives **path segments, query params, headers, cookies, forms, files and JSON
  bodies** — inferred, or explicit with `Annotated` markers.
- **Pydantic in, validated Pydantic out.** The return annotation is the response model, so
  `client.get_user(1)` is typed as `User` for mypy and your IDE.
- **Typed errors and hooks**: non-2xx responses raise `NotFoundError`, `RateLimitError`, …
  and every request can be observed through hooks.
- Ready for real APIs: auth, automatic token refresh (even on custom conditions), and
  resource CRUD with paging that needs no page-loop code.

## Installation

```bash
pip install asas-py             # + Pydantic + httpx (the default engine)
pip install "asas-py[requests]" # + the optional sync-only requests engine
```

Python 3.10+ (see [Documentation](https://heshammoawad.github.io/asas-py/) for the Arabic guide).

## Quick start

Subclass a client and declare your endpoints. That's it.

```python
from pydantic import BaseModel

from asas import AsasClient, get


class Todo(BaseModel):
    id: int
    todo: str
    completed: bool


class TodoClient(AsasClient):
    @get("/todos/{id}")
    def get_todo(self, id: int) -> Todo: ...


with TodoClient(base_url="https://dummyjson.com") as client:
    task = client.get_todo(1)       # typed: Todo
    print(task.todo)
```

`id` is a path placeholder and the return annotation `Todo` validates the JSON response. The
method body is never executed, so it is just `...`. Want async? Use
`async def` with `AsasAsyncClient` — the decorators are identical. This snippet runs as-is
against [dummyjson.com](https://dummyjson.com) (a free public REST API).

### Try it live

```python
from typing import List

from pydantic import BaseModel

from asas import AsasClient, get


class Product(BaseModel):
    id: int
    title: str
    price: float


class ProductPage(BaseModel):
    products: List[Product]


class StoreClient(AsasClient):
    @get("/products")
    def products(self) -> ProductPage: ...

    def product_list(self) -> List[Product]:
        return self.products().products


client = StoreClient(base_url="https://dummyjson.com")
first = client.product_list()
print(f"{len(first)} products, first: {first[0].title} (${first[0].price})")
```

### Resources & lazy pagination — no page-loop code

```python
from pydantic import BaseModel

from asas import AsasClient, AsasResource, OffsetPaginator


class User(BaseModel):
    id: int
    name: str


class Users(AsasResource[User]):
    path = "/users"
    paginator = OffsetPaginator(limit=100, items_key="users")


class Client(AsasClient):
    users = Users()


client = Client(base_url="https://api.example.com")
for user in client.users:          # pages fetched on demand, loop ends itself
    print(user.name)

single = client.users.get(42)      # generated CRUD, too: typed as User
```

### Parameters, errors and hooks

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, Header, Hooks, NotFoundError, Query, get


class User(BaseModel):
    id: int
    name: str


class Users(AsasClient):
    @get("/users/{id}")
    def get_user(
        self,
        id: int,
        expand: Annotated[str | None, Query(alias="x-expand")] = None,
        trace: Annotated[str | None, Header("X-Trace")] = None,
    ) -> User: ...


hooks = Hooks(on_response=[lambda req, res: print(req.method, req.url, res.status_code)])
with Users(base_url="https://api.example.com", hooks=hooks) as client:
    try:
        user = client.get_user(1, trace="abc")
    except NotFoundError:
        user = None
```

### Authentication & automatic refresh

```python
from asas import AsasClient, RefreshingBearerAuth, get, refresh_on_keyword

auth = RefreshingBearerAuth(
    "expired-token",
    refresh_callback=lambda: mint_new_token(),
    refresh_when=refresh_on_keyword("token_expired"),  # refresh on a 200, too
)


class MyClient(AsasClient):
    @get("/me")
    def me(self) -> dict: ...


client = MyClient(base_url="https://api.example.com", auth=auth)
```

## Features

- **Sync & async clients** that share the same `@get`/`@post`/`@put`/`@delete`/`@patch`
  decorators — Asas auto-detects `async def`.
- **Typed endpoints** — the return annotation drives parsing, so callers see the exact
  signature you declared (`assert_type(client.get_user(1), User)` passes under `mypy --strict`).
- **Parameter routing** — path placeholders, Pydantic-model bodies, and query params inferred
  from a single method signature, or explicit with `Path` / `Query` / `Header` / `Cookie` /
  `Body` / `Form` / `File` markers and aliases.
- **Typed errors** — non-2xx responses raise `NotFoundError`, `RateLimitError`, … (all
  `AsasError`s), plus `ResponseValidationError` and `TransportError`.
- **Hooks** — `on_request` / `on_response` / `on_error` on the client or an endpoint.
- **Resources + lazy pagination** — the generic `AsasResource[User]` gives `list`/`get`/`create`/`update`/
  `delete` and iterator-style paging (page-number, offset, cursor, and Link-header strategies).
- **Authentication out of the box** — `NoAuth`, `BasicAuth`, `BearerAuth`, `APIKeyAuth`
  (header/query/cookie), `RefreshingBearerAuth`, and `CompositeAuth`, with swappable runtime
  auth and easy-to-test refresh **conditions**.
- **Transport-agnostic core** — `httpx` is bundled; bring your own engine (an optional,
  sync-only `requests` engine ships behind the `[requests]` extra).

## Roadmap

Planned and share-worthy next features:

- [ ] **OpenAPI / Swagger client generation** — generate a full typed client (Pydantic models
      + client code) straight from an OpenAPI schema.
- [ ] **GraphQL support** — query / mutation / subscription decorators with typed responses.
- [ ] **Testing module** — fixtures and helpers to make writing client tests trivial (respx
      mocks, base harnesses, captured requests).
- [ ] **Middleware & retries** — retry/backoff and async hooks (synchronous lifecycle hooks
      shipped in 0.2).
- [ ] **Cookie & session helpers** — first-class session management, cookie jars, and CSRF
      handling.

> Have a feature in mind? [Open an issue](https://github.com/heshammoawad/asas-py/issues) or
> start a discussion — contributions and ideas are very welcome.

## Contributing

Contributions of all kinds are welcome — bug reports, documentation, examples, and features.

1. **Fork & clone** the repo.
2. **Set up:** `make dev-install` (installs deps + git hooks).
3. **Develop:** write your code with type hints, then `make format` and `make lint`.
4. **Test:** `make test`.
5. **Commit** with a clear message and open a **Pull Request**.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and coding standards.

## Documentation

Full docs (English + العربية): [heshammoawad.github.io/asas-py](https://heshammoawad.github.io/asas-py/)

- [Clients](docs/clients.md)
- [Routing](docs/routing.md)
- [Parameters](docs/parameters.md)
- [Request Bodies & Responses](docs/request-response.md)
- [Errors](docs/errors.md)
- [Hooks](docs/hooks.md)
- [Resources & Pagination](docs/resources.md)
- [Authentication](docs/authentication.md)
- [Engines & Transports](docs/engines.md)
- [Core Models](docs/models.md)
- [Migrating to 0.2](docs/migration-0.2.md)

## License

Released under the [MIT License](LICENSE).
