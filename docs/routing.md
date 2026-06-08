# Routing & Parameters

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
@get(path, response_model=None, use_auth=True)
```

- **`path`** — the endpoint path, appended to the client's `base_url`. May contain
  `{placeholder}` segments.
- **`response_model`** — an optional Pydantic type used to validate the response. See
  [Request Bodies & Responses](request-response.md).
- **`use_auth`** — set to `False` to skip the client's auth for this endpoint (see below).

## The method signature convention

A decorated method receives the **parsed result as its first argument after `self`**, then
its own parameters:

```python
@get("/users/{id}")
def get_user(self, response: Response, id: int):
    #              ^^^^^^^^^^^^^^^^^^  ^^^^^^^
    #              injected by Asas   supplied by the caller
    return response.json()
```

You never pass the first argument yourself — Asas injects it. Everything after it is part of
your public method signature and is routed into the request.

## Parameter routing

When you call the method, Asas inspects each of your parameters and routes it **by name and
type**:

| Parameter | Routed to |
| --- | --- |
| Name matches a `{placeholder}` in the path | Substituted into the URL |
| A Pydantic `BaseModel` (or a list of them) | The JSON request body |
| Anything else that isn't `None` | A query parameter |

```python
from pydantic import BaseModel
from asas import AsasClient, post, Response

class CreateUser(BaseModel):
    name: str
    email: str

class MyClient(AsasClient):
    @post("/teams/{id}/users")
    def create_user(self, response: Response, id: int, payload: CreateUser, team: str):
        return response.json()

client = MyClient(base_url="https://api.example.com")
client.create_user(
    id=42,                                                  # -> URL path
    payload=CreateUser(name="Ada", email="ada@x.com"),     # -> JSON body
    team="core",                                            # -> query string
)
# POST https://api.example.com/teams/42/users?team=core
# body: {"name": "Ada", "email": "ada@x.com"}
```

!!! warning "Bodies must be Pydantic models"
    A plain `dict` is **not** treated as a body — it becomes query parameters. Wrap body
    data in a `BaseModel` to send it as JSON. See
    [Request Bodies & Responses](request-response.md).

A parameter whose value is `None` is dropped entirely, which makes optional query parameters
easy:

```python
@get("/search")
def search(self, response: Response, q: str, page: int = None):
    return response.json()

client.search(q="asas")            # GET /search?q=asas
client.search(q="asas", page=2)    # GET /search?q=asas&page=2
```

## The return convention

The decorator inspects what your method body returns:

- If the body returns `None` (e.g. it is empty, written just for typing), the decorator
  returns the **parsed result** it injected.
- If the body returns a value, **your value wins** — use this to post-process the result.

=== "Empty body (return the parsed result)"

    ```python
    @get("/users/{id}", response_model=User)
    def get_user(self, user: User, id: int) -> User:
        ...        # body returns None -> Asas returns `user`
    ```

=== "Post-processing"

    ```python
    @get("/users/{id}")
    def get_username(self, response: Response, id: int) -> str:
        return response.json()["name"]   # your value is returned
    ```

## Sync and async, one decorator

The same decorators work on both `def` and `async def` methods — Asas detects coroutine
functions automatically and uses the engine's async path. There is nothing extra to import.

```python
class AsyncClient(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, response: Response, id: int):
        return response.json()
```

!!! note
    Calling an `async def` endpoint on a sync engine (or vice versa) raises a clear
    `TypeError` telling you which protocol the engine is missing.

## Per-endpoint auth control

Even when the client has a global auth strategy, you can disable it for specific public
endpoints with `use_auth=False`:

```python
class MyClient(AsasClient):
    @get("/public-data", use_auth=False)
    def get_public(self, response: Response):
        return response.json()
```

This is also what you use for the login endpoint that *produces* your token — see the
runtime-auth example in [Clients](clients.md).
