# Engines & Transports

Asas separates *what* a request is from *how* it travels over the network. An **engine** is
the transport layer. The core speaks plain [`Request` / `Response`](models.md) dataclasses,
so any HTTP library can be plugged in by implementing an engine.

## The engine protocols

Engines are `runtime_checkable` Protocols — there is no base class to inherit. A sync engine
implements two methods, an async engine implements their async twins:

=== "SyncEngine"

    ```python
    class SyncEngine(Protocol):
        def send(self, request: Request) -> Response: ...
        def close(self) -> None: ...
    ```

=== "AsyncEngine"

    ```python
    class AsyncEngine(Protocol):
        async def asend(self, request: Request) -> Response: ...
        async def aclose(self) -> None: ...
    ```

When you call a decorated method, Asas checks that the engine supports the right mode and
raises a clear `TypeError` if, say, you call an `async def` endpoint on a sync-only engine.

## The bundled httpx engine

`HTTPXSyncEngine` and `HTTPXAsyncEngine` are the reference implementations and the default
when no engine is passed. They lazily create the underlying `httpx` client and forward any
constructor `**kwargs` to it.

```python
from asas import AsasClient, HTTPXSyncEngine

# These two clients are equivalent:
client = AsasClient(base_url="https://api.example.com", timeout=10.0)
client = AsasClient(
    base_url="https://api.example.com",
    engine=HTTPXSyncEngine(timeout=10.0),
)
```

Passing the engine explicitly is useful when you want to share one engine between clients or
configure it in a single place.

## Writing a custom engine

To support another transport (`requests`, `aiohttp`, an in-memory test double, …),
implement the protocol and convert to and from `asas.core.models`. Nothing else in the
framework needs to change.

```python
import requests
from asas.core.models import Request, Response

class RequestsEngine:
    def __init__(self) -> None:
        self.session = requests.Session()

    def send(self, request: Request) -> Response:
        payload = request.payload
        resp = self.session.request(
            method=request.method,
            url=request.url,
            params=request.params,
            headers=request.headers,
            json=payload.json if payload else None,
        )
        return Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
            text=resp.text,
        )

    def close(self) -> None:
        self.session.close()
```

Use it by passing an instance as `engine=`:

```python
from asas import AsasClient

client = AsasClient(base_url="https://api.example.com", engine=RequestsEngine())
```

!!! tip "Testing without a network"
    A custom engine that returns canned `Response` objects is the simplest way to unit-test
    a client. The Asas test suite itself mocks the `httpx` engine with
    [`respx`](https://lundberg.github.io/respx/).

!!! note "`**kwargs` only configure the default engine"
    The client's `**kwargs` passthrough targets the bundled `httpx` engine. A custom engine
    should be configured on its own constructor before you pass it in.
