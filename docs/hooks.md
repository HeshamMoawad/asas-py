# Hooks

Hooks let you observe or modify every request, response and error without touching each
endpoint: logging, tracing headers, metrics and so on. They are plain synchronous callables
collected in a `Hooks` dataclass.

```python
from collections.abc import Callable
from dataclasses import dataclass, field

from asas import AsasError, Request, Response


@dataclass
class Hooks:
    on_request: list[Callable[[Request], Request | None]] = field(default_factory=list)
    on_response: list[Callable[[Request, Response], None]] = field(default_factory=list)
    on_error: list[Callable[[AsasError], None]] = field(default_factory=list)
```

| Hook list | Signature | Purpose |
| --- | --- | --- |
| `on_request` | `(Request) -> Request \| None` | Mutate the request and return `None`, or return a replacement |
| `on_response` | `(Request, Response) -> None` | Observe every response |
| `on_error` | `(AsasError) -> None` | Observe an error before it is raised |

## Attaching hooks

Pass hooks to the client, to an endpoint, or both:

```python
import logging

from asas import AsasClient, AsasError, Hooks, Request, Response, get

log = logging.getLogger("api")


def stamp(request: Request) -> None:
    request.headers["X-Client"] = "asas-demo"


def log_response(request: Request, response: Response) -> None:
    log.info("%s %s -> %s", request.method, request.url, response.status_code)


def log_error(error: AsasError) -> None:
    log.warning("request failed: %s", error)


class Api(AsasClient):
    @get("/ping", hooks=Hooks(on_response=[lambda req, res: log.debug("ping")]))
    def ping(self) -> dict:
        raise NotImplementedError


client = Api(
    base_url="https://api.example.com",
    hooks=Hooks(on_request=[stamp], on_response=[log_response], on_error=[log_error]),
)
```

`client.hooks` is a public attribute, so you can append to it later:
`client.hooks.on_request.append(stamp)`.

## Ordering

For each list, **client hooks run first, then endpoint hooks**, each in the order they appear
in the list. When `on_request` hooks chain, each receives the request produced by the one
before it.

```python
from asas import Hooks, Request


def add_trace(request: Request) -> Request | None:
    request.headers["X-Trace"] = "1"      # mutate and return None...
    return None


def replace(request: Request) -> Request | None:
    return Request(method="GET", url=request.url)   # ...or return a replacement


hooks = Hooks(on_request=[add_trace, replace])
```

## Where hooks run in the pipeline

```
build request → auth.apply (if use_auth) → on_request* → engine.send → on_response*
    → on a 401 refresh / challenge: rebuild → auth.apply → on_request* → send → on_response*
      (exactly once)
    → status check   (HTTPStatusError)
    → parse response (ResponseValidationError)
    → return

TransportError, HTTPStatusError, ResponseValidationError  →  on_error*  →  raise
```

- `on_request` runs after auth has been applied, so hooks see the final headers. On a refresh
  or challenge retry the request is rebuilt, and `on_request` and `on_response` run again.
- `on_error` is observational. It runs **before** the error is raised and cannot suppress it.
  It fires only for `TransportError`, `HTTPStatusError` and `ResponseValidationError` raised
  by the pipeline. A `-> Response` endpoint never raises on HTTP status, so `on_error` is not
  called for a status there; a `TransportError` is still raised and still fires `on_error`.
- An exception raised **inside a hook** propagates unchanged, and `on_error` is not called
  for it.
- Resources (`AsasResource`) run through the same pipeline, so client hooks apply to their
  CRUD and pagination requests too.

## Hooks must not block

Hooks are synchronous callables, and the same hooks serve sync and async clients. In an
`AsasAsyncClient` they run on the event loop, so a hook must **not block on I/O** (no network
calls, no file reads, no `time.sleep`). Keep them quick: log, set a header, increment a
counter. Async hooks are not supported in 0.2.
