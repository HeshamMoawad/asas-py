# Routing

Asas exposes one decorator per HTTP method. Each turns a method on your client into a typed
endpoint.

| Decorator | HTTP method |
| --- | --- |
| `@get` | `GET` |
| `@post` | `POST` |
| `@put` | `PUT` |
| `@delete` | `DELETE` |
| `@patch` | `PATCH` |

All five take the same arguments:

```python
def get(
    path, *, headers=None, timeout=None, use_auth=True, raise_for_status=None, hooks=None
): ...
```

- **`path`** — the endpoint path, appended to the client's `base_url`. May contain
  `{placeholder}` segments.
- **`headers`** — a mapping of headers sent with this endpoint only. See
  [header precedence](parameters.md#header-precedence).
- **`timeout`** — a per-request timeout in seconds. It is applied by the bundled `httpx` and
  `requests` engines.
- **`use_auth`** — set to `False` to skip the client's auth for this endpoint (see below).
- **`raise_for_status`** — `True` or `False` to override the client's setting for this
  endpoint; `None` (the default) inherits it. See [Errors](errors.md#when-errors-are-raised).
- **`hooks`** — a [`Hooks`](hooks.md) instance that runs after the client's hooks.

`path` is the only positional argument; everything else is keyword-only. The `response_model`
argument from 0.1 no longer exists — the return annotation replaces it.

## Declaring an endpoint

The **return annotation** tells Asas how to parse the response, and the **parameters** tell it
how to build the request. The method body is never executed, so the convention is to write
`raise NotImplementedError` (a bare `...` is rejected by `mypy --strict` as `[empty-body]`):

```python
from pydantic import BaseModel

from asas import AsasClient, get


class User(BaseModel):
    id: int
    name: str


class MyClient(AsasClient):
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError


client = MyClient(base_url="https://api.example.com")
user = client.get_user(1)       # GET /users/1  ->  User
```

The decorators are typed so callers see the signature you wrote unchanged:
`client.get_user(1)` is a `User` to mypy and to your IDE. No argument is injected, and nothing
is passed to the method body.

If you want to post-process a result, write an ordinary method that calls the endpoint, or use
a [hook](hooks.md):

```python
class MyClient(AsasClient):
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError

    def get_username(self, id: int) -> str:
        return self.get_user(id).name
```

## Return annotations

| Return annotation | Result |
| --- | --- |
| `Response` | the raw [`Response`](models.md#response); never raises on status |
| `None` | `None`; the body is discarded |
| `bytes` | `response.content` |
| `str` | `response.text` |
| any other type `T` | the body validated as `T` with a Pydantic `TypeAdapter` |

See [Request Bodies & Responses](request-response.md) for details, including empty bodies.
A missing return annotation raises `TypeError` — use `-> Response` when you want the raw
response.

## How parameters are routed

Every parameter is routed by a marker, or inferred from its annotation when you give none:

| Parameter | Routed to |
| --- | --- |
| Name matches a `{placeholder}` in the path | Substituted into the URL |
| Annotated as a `BaseModel`, `list[BaseModel]` or `dict` | The JSON request body |
| Anything else | A query parameter |

```python
from pydantic import BaseModel

from asas import AsasClient, post


class CreateUser(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str


class MyClient(AsasClient):
    @post("/teams/{id}/users")
    def create_user(self, id: int, payload: CreateUser, team: str) -> User:
        raise NotImplementedError


client = MyClient(base_url="https://api.example.com")
client.create_user(
    42,                                                  # -> URL path
    CreateUser(name="Ada", email="ada@x.com"),           # -> JSON body
    team="core",                                         # -> query string
)
# POST https://api.example.com/teams/42/users?team=core
# body: {"name": "Ada", "email": "ada@x.com"}
```

Routing is decided from the **annotations at decoration time**, not from the values you pass at
call time. For headers, cookies, forms, files and aliases, use the markers described in
[Parameters](parameters.md).

A parameter whose value is `None` is omitted from the query, headers, cookies and form, which
makes optional parameters easy:

```python
class SearchClient(AsasClient):
    @get("/search")
    def search(self, q: str, page: int | None = None) -> dict:
        raise NotImplementedError


client = SearchClient(base_url="https://api.example.com")
client.search("asas")            # GET /search?q=asas
client.search("asas", page=2)    # GET /search?q=asas&page=2
```

!!! note "Declaration mistakes fail early"
    Mistakes such as a `{placeholder}` with no matching parameter, a missing annotation, or
    `*args` / `**kwargs` on an endpoint raise `TypeError` when the class is defined. See
    [Parameters](parameters.md#declaration-errors).

!!! warning "Forward references are checked on the first call"
    If the return or a parameter type is not defined yet when the endpoint is decorated (for
    example a model declared further down the module, with string annotations), Asas defers
    compilation to the **first call**. Declaration `TypeError`s for such an endpoint then
    surface on that first call instead of at import. Define models at module level: models
    created inside a function body cannot be resolved from string annotations.

## Sync and async, one decorator

The same decorators work on both `def` and `async def` methods — Asas detects coroutine
functions automatically and uses the engine's async path. `async def ... -> User` returns a
`User` when awaited.

```python
from pydantic import BaseModel

from asas import AsasAsyncClient, get


class User(BaseModel):
    id: int
    name: str


class AsyncClient(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, id: int) -> User:
        raise NotImplementedError
```

!!! note
    Calling an `async def` endpoint on a sync engine (or vice versa) raises a clear
    `TypeError` telling you which protocol the engine is missing.

## Per-endpoint auth control

Even when the client has a global auth strategy, you can disable it for specific public
endpoints with `use_auth=False`:

```python
from asas import AsasClient, get


class MyClient(AsasClient):
    @get("/public-data", use_auth=False)
    def get_public(self) -> dict:
        raise NotImplementedError
```

This is also what you use for the login endpoint that *produces* your token — see the
runtime-auth example in [Clients](clients.md).
