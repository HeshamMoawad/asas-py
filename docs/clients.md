# Clients

A **client** is the object you subclass to describe an API. It holds three things: the
`base_url`, the transport `engine`, and an optional `auth` strategy. Asas provides two
ready-made base classes.

| Class | Mode | Default engine |
| --- | --- | --- |
| `AsasClient` | synchronous | `HTTPXSyncEngine` |
| `AsasAsyncClient` | asynchronous | `HTTPXAsyncEngine` |

## Defining a client

Subclass the base that matches your code style and add decorated methods:

=== "Synchronous"

    ```python
    from asas import AsasClient, get, Response

    class GitHubClient(AsasClient):
        @get("/users/{username}")
        def get_user(self, response: Response, username: str):
            return response.json()

    client = GitHubClient(base_url="https://api.github.com")
    user = client.get_user(username="torvalds")
    ```

=== "Asynchronous"

    ```python
    from asas import AsasAsyncClient, get, Response

    class GitHubClient(AsasAsyncClient):
        @get("/users/{username}")
        async def get_user(self, response: Response, username: str):
            return response.json()

    async def main():
        client = GitHubClient(base_url="https://api.github.com")
        user = await client.get_user(username="torvalds")
        await client.engine.aclose()
    ```

## Constructor arguments

Both clients share the same signature:

```python
AsasClient(base_url="", engine=None, auth=None, **kwargs)
```

- **`base_url`** — prefix joined with each decorated path. A trailing slash is stripped, so
  `https://api.example.com` and `https://api.example.com/` behave identically.
- **`engine`** — a transport implementing the engine protocol. Defaults to the bundled
  `httpx` engine. See [Engines & Transports](engines.md).
- **`auth`** — an optional authentication strategy. See [Authentication](authentication.md).
- **`**kwargs`** — any extra keyword arguments are forwarded to the underlying `httpx`
  client constructor (when the default engine is used).

```python
# Extra kwargs flow straight through to httpx.Client / httpx.AsyncClient
client = GitHubClient(
    base_url="https://api.github.com",
    timeout=10.0,
    headers={"Accept": "application/vnd.github+json"},
)
```

!!! note "Custom engines ignore `**kwargs`"
    The `**kwargs` passthrough only applies when Asas creates the default `httpx` engine.
    If you pass your own `engine=`, configure that engine directly instead.

## Swapping auth at runtime

`auth` is a settable property, so you can change credentials after construction — for
example, right after a login call returns a token:

```python
from asas import AsasClient, BearerAuth, post, Response
from pydantic import BaseModel

class Credentials(BaseModel):
    username: str
    password: str

class ApiClient(AsasClient):
    @post("/auth/login", use_auth=False)
    def login(self, response: Response, credentials: Credentials):
        return response.json()

client = ApiClient(base_url="https://api.example.com")

# 1. Authenticate without any auth header...
data = client.login(credentials=Credentials(username="ada", password="secret"))

# 2. ...then attach the returned token for every subsequent call.
client.auth = BearerAuth(data["token"])
```

Setting `client.auth = None` removes authentication entirely.

## Closing the client

The transport keeps a connection pool open. Close it when you are done — especially for the
async client, which must be awaited:

=== "Synchronous"

    ```python
    client.engine.close()
    ```

=== "Asynchronous"

    ```python
    await client.engine.aclose()
    ```
