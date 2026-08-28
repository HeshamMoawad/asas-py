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

## The bundled requests engine (optional extra)

Asas also ships an engine built on [`requests`](https://requests.readthedocs.io/). Install it
with the `requests` extra:

```bash
pip install "asas-py[requests]"
```

`httpx` remains the default engine that ships with `asas-py`; the `requests` engine is an
optional alternative you opt into per client. Import it from its own module (never imported by
the top-level package) and pass it via `engine=`:

```python
from asas import AsasClient
from asas.engines.requests import RequestsSyncEngine

client = AsasClient(base_url="https://api.example.com", engine=RequestsSyncEngine())
```

It lazily creates a `requests.Session` and forwards any constructor `**kwargs` to it, just like
the httpx engine. It also supports JSON bodies, raw `data`, `files`, query params, and custom
headers through the same [`Payload`](models.md).

!!! warning "Synchronous only"
    The `requests` library has no native async support, so the requests engine is
    **synchronous only** — there is no `RequestsAsyncEngine`. Use it with `AsasClient` (not
    `AsasAsyncClient`). Calling an async endpoint on a client backed by this engine raises a
    `TypeError` explaining that it is sync-only; switch to `AsasClient` or use the httpx
    engine (`HTTPXAsyncEngine`) for async.

## Writing a custom engine

To support another transport (`aiohttp`, `urllib`, an in-memory test double, …), implement the
protocol and convert to and from `asas.core.models`. Nothing else in the framework needs to
change. (A `requests` engine is already bundled — see
[above](#the-bundled-requests-engine-optional-extra); you don't need to write your own.)

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
