# Clients

A **client** is the object you subclass to describe an API. It holds three things: the
`base_url`, the transport `engine`, and an optional `auth` strategy. Asas provides two
ready-made base classes.

| Class | Mode | Default engine |
| --- | --- | --- |
| `AsasClient` | synchronous | `HTTPXSyncEngine` |
| `AsasAsyncClient` | asynchronous | `HTTPXAsyncEngine` |

## Defining a client

Subclass the base that matches your code style and add decorated methods. Using the client as
a context manager closes it for you:

=== "Synchronous"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get


    class GitHubUser(BaseModel):
        login: str
        id: int


    class GitHubClient(AsasClient):
        @get("/users/{username}")
        def get_user(self, username: str) -> GitHubUser:
            raise NotImplementedError


    with GitHubClient(base_url="https://api.github.com") as client:
        user = client.get_user("torvalds")
    ```

=== "Asynchronous"

    ```python
    from pydantic import BaseModel

    from asas import AsasAsyncClient, get


    class GitHubUser(BaseModel):
        login: str
        id: int


    class GitHubClient(AsasAsyncClient):
        @get("/users/{username}")
        async def get_user(self, username: str) -> GitHubUser:
            raise NotImplementedError


    async def main() -> None:
        async with GitHubClient(base_url="https://api.github.com") as client:
            user = await client.get_user("torvalds")
    ```

## Constructor arguments

Both clients share the same signature. Everything after `base_url` is **keyword-only**:

```python
def __init__(
    self,
    base_url="",
    *,
    engine=None,
    auth=None,
    hooks=None,
    raise_for_status=True,
    **engine_kwargs,
): ...
```

- **`base_url`** — prefix joined with each decorated path. A trailing slash is stripped, so
  `https://api.example.com` and `https://api.example.com/` behave identically.
- **`engine`** — a transport implementing the engine protocol. Defaults to the bundled
  `httpx` engine. See [Engines & Transports](engines.md).
- **`auth`** — an optional authentication strategy. See [Authentication](authentication.md).
- **`hooks`** — an optional [`Hooks`](hooks.md) instance. Also available as the public
  attribute `client.hooks`.
- **`raise_for_status`** — whether non-2xx responses raise a [typed error](errors.md).
  Endpoints can override it. Default `True`.
- **`**engine_kwargs`** — any extra keyword arguments are forwarded to the underlying `httpx`
  client constructor (when the default engine is used).

```python
# Extra kwargs flow straight through to httpx.Client / httpx.AsyncClient
client = GitHubClient(
    base_url="https://api.github.com",
    timeout=10.0,
    headers={"Accept": "application/vnd.github+json"},
)
```

The default engine applies these client defaults to every request: the `headers`, `timeout`
and so on you pass here take effect, and per-endpoint values (`timeout=`, `headers=`) are
layered on top.

!!! note "Custom engines ignore `**engine_kwargs`"
    The passthrough only applies when Asas creates the default `httpx` engine.
    If you pass your own `engine=`, configure that engine directly instead.

## Swapping auth at runtime

`auth` is a settable property, so you can change credentials after construction — for
example, right after a login call returns a token:

```python
from asas import AsasClient, BearerAuth, post
from pydantic import BaseModel

class Credentials(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    token: str

class ApiClient(AsasClient):
    @post("/auth/login", use_auth=False)
    def login(self, credentials: Credentials) -> Token:
        raise NotImplementedError

client = ApiClient(base_url="https://api.example.com")

# 1. Authenticate without any auth header...
data = client.login(Credentials(username="ada", password="secret"))

# 2. ...then attach the returned token for every subsequent call.
client.auth = BearerAuth(data.token)
```

Setting `client.auth = None` removes authentication entirely.

## Closing the client

The transport keeps a connection pool open. The simplest way to release it is a context
manager, which closes the client on exit even if the block raises:

=== "Synchronous"

    ```python
    with GitHubClient(base_url="https://api.github.com") as client:
        client.get_user("torvalds")
    # closed here
    ```

=== "Asynchronous"

    ```python
    async def main() -> None:
        async with GitHubClient(base_url="https://api.github.com") as client:
            await client.get_user("torvalds")
        # closed here
    ```

Without a context manager, call `client.close()` (sync) or `await client.aclose()` (async).

!!! warning "Closing a client closes its engine"
    The client always closes its engine, **even one you passed in**. If you share one engine
    between several clients, closing any one of them closes it for all. In that case manage
    the engine's lifetime yourself: close the engine directly (`engine.close()` /
    `await engine.aclose()`) when the last client is done, and don't use the clients as
    context managers.
