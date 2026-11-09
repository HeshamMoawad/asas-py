# Core Models

At the heart of Asas are three plain dataclasses in `asas.core.models`: `Request`,
`Response`, and `Payload`. They know nothing about `httpx` or any specific transport — they
are the shared language every layer speaks, which is exactly what lets
[engines](engines.md) and [auth strategies](authentication.md) be swapped freely.

```
@get method  →  Request  →  auth.apply()  →  engine.send()  →  Response  →  parsed return value
```

## Request

The protocol-agnostic request that auth strategies mutate and engines send.

```python
@dataclass
class Request:
    method: str
    url: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] = {}
    cookies: dict[str, str] = {}
    payload: Payload | None = None
    timeout: float | None = None
```

| Field | Meaning |
| --- | --- |
| `method` | HTTP method, e.g. `"GET"` |
| `url` | Fully built URL (`base_url` + resolved path) |
| `params` | Query parameters |
| `headers` | Request headers — where most auth strategies write |
| `cookies` | Cookies to send; engines must send them (`APIKeyAuth` in a cookie writes here) |
| `payload` | The request body, if any (see [`Payload`](#payload)) |
| `timeout` | Optional per-request timeout |

An [`Auth.apply`](authentication.md#how-auth-is-applied) method receives a `Request`, mutates
its `headers`, `cookies` or `params`, and returns it.

## Response

The protocol-agnostic response your engine produces. Asas parses it according to the
endpoint's return annotation.

```python
@dataclass
class Response:
    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str

    def json(self) -> Any:
        ...
```

| Member | Meaning |
| --- | --- |
| `status_code` | HTTP status code |
| `headers` | Response headers |
| `content` | Raw response body as `bytes` |
| `text` | Response body decoded to `str` |
| `json()` | Parse `content` as JSON |

When an endpoint is annotated `-> Response`, this object is what the call returns — call
`response.json()` to read the body. See [Request Bodies & Responses](request-response.md).

## Payload

A general container for request data, carried on `Request.payload`.

```python
@dataclass
class Payload:
    data: dict[str, Any] | bytes | None = None
    json: Any = None
    files: dict[str, Any] | None = None
    headers: dict[str, str] = {}
```

| Field | Meaning |
| --- | --- |
| `data` | Form fields (a `dict`) or a raw body (`bytes`) |
| `json` | A JSON body of any shape (object, array, scalar) — what models are dumped into |
| `files` | File uploads, sent as multipart together with any form `data` |
| `headers` | Payload-specific headers |

When you pass a Pydantic model to an endpoint, Asas dumps it (JSON-safe, by alias) and stores
the result in `Payload.json`; `Form` and `File` parameters fill `data` and `files`. See [Request Bodies & Responses](request-response.md) for how that routing
works.

!!! note "You rarely build these by hand"
    Asas constructs `Request` and `Payload` for you from your method call, and engines build
    `Response`. You work with these types directly mainly when writing a
    [custom engine](engines.md#writing-a-custom-engine) or a
    [custom auth strategy](authentication.md#how-auth-is-applied).
