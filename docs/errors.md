# Errors

Every error Asas raises derives from `AsasError`, and all of them are exported from the top
level package. A non-2xx response raises a typed exception by default, so a failed call can
no longer be mistaken for a successful one.

## The hierarchy

```
AsasError
├── HTTPStatusError(request, response)          .status_code
│   ├── ClientError                              4xx fallback
│   │   ├── BadRequestError            400
│   │   ├── UnauthorizedError          401
│   │   ├── ForbiddenError             403
│   │   ├── NotFoundError              404
│   │   ├── ConflictError              409
│   │   ├── UnprocessableEntityError   422
│   │   └── RateLimitError             429      .retry_after: float | None
│   └── ServerError                              5xx fallback
│       ├── InternalServerError        500
│       └── ServiceUnavailableError    503
├── ResponseValidationError(response, error)    wraps pydantic / JSON errors
└── TransportError(message, request)            raised by engines, chained with `from`
```

- **`HTTPStatusError`** has `request`, `response` and `status_code`. The most specific class
  for the status wins; otherwise a 4xx raises `ClientError`, a 5xx raises `ServerError`, and
  any other non-2xx status (1xx, 3xx) raises plain `HTTPStatusError`.
- **`ResponseValidationError`** has `response` and `error`. It is raised when the body is not
  valid JSON, does not match the return type, or is empty for a type that does not admit
  `None`.
- **`TransportError`** has `request`. It means no response was produced: a connection
  failure, a timeout, and so on. The original library exception is chained as `__cause__`.

The message of a status error looks like
`GET https://api.example.com/users/1 → 404 Not Found: <first 200 characters of the body>`.

## When errors are raised

Whether a non-2xx status raises is resolved in this order:

1. the endpoint's `raise_for_status=` argument, if it is not `None`
2. the client's `raise_for_status` (default `True`)

```python
from pydantic import BaseModel

from asas import AsasClient, get


class User(BaseModel):
    id: int
    name: str


class Users(AsasClient):
    @get("/users/{id}")
    def get_user(self, id: int) -> User: ...

    @get("/users/{id}/lenient", raise_for_status=False)
    def get_user_lenient(self, id: int) -> dict: ...


strict = Users(base_url="https://api.example.com")
lenient = Users(base_url="https://api.example.com", raise_for_status=False)
```

Status errors are raised **after** the auth refresh or challenge retry has been attempted. So
an expired token that refreshes successfully never surfaces as `UnauthorizedError`; one that
still returns `401` after the single retry does.

### Opting out with `-> Response`

An endpoint annotated `-> Response` **never raises on HTTP status**, whatever
`raise_for_status` says, so `on_error` is not called for a status. A `TransportError` is still
raised and still fires `on_error`. Use it when you want to inspect the status yourself:

```python
from asas import AsasClient, Response, get


class Users(AsasClient):
    @get("/users/{id}")
    def probe(self, id: int) -> Response: ...


client = Users(base_url="https://api.example.com")
response = client.probe(1)
if response.status_code == 404:
    print("no such user")
```

`TransportError` is still raised for a `-> Response` endpoint, because no response exists.

## Catching errors

Catch the most specific class you can handle, then fall back to a broader one:

```python
from asas import (
    AsasError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TransportError,
)

try:
    user = client.get_user(1)
except NotFoundError:
    user = None
except RateLimitError as exc:
    wait = exc.retry_after   # seconds, or None
except ServerError as exc:
    print("server problem", exc.status_code)
except TransportError as exc:
    print("could not reach the server", exc.request.url)
except AsasError:
    raise
```

### Reading `retry_after`

`RateLimitError.retry_after` is the number of seconds the server asked you to wait. Asas
parses the `Retry-After` header as delta-seconds or as an HTTP date (converted to seconds from
now, never below `0`). It is `None` when the header is missing or cannot be parsed.

```python
import time

from asas import RateLimitError

try:
    client.get_user(1)
except RateLimitError as exc:
    time.sleep(exc.retry_after or 1.0)
    client.get_user(1)
```

## Writing an engine that raises `TransportError`

Engines must wrap their library's transport exceptions in `TransportError`; see
[Engines](engines.md#the-engine-contract).

## Observing errors

[Hooks](hooks.md) can observe every error before it is raised through `on_error`.
