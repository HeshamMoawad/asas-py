# Core Models

At the heart of Asas are three plain dataclasses in `asas.core.models`: `Request`,
`Response`, and `Payload`. They know nothing about `httpx` or any specific transport — they
are the shared language every layer speaks, which is exactly what lets
[engines](engines.md) and [auth strategies](authentication.md) be swapped freely.

```
@get method  →  Request  →  auth.apply()  →  engine.send()  →  Response  →  your method
```

## Request

The protocol-agnostic request that auth strategies mutate and engines send.

```python
@dataclass
class Request:
    method: str
    url: str
    params: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = {}
    payload: Optional[Payload] = None
    timeout: Optional[float] = None
```

| Field | Meaning |
| --- | --- |
| `method` | HTTP method, e.g. `"GET"` |
| `url` | Fully built URL (`base_url` + resolved path) |
| `params` | Query parameters |
| `headers` | Request headers — where most auth strategies write |
| `payload` | The request body, if any (see [`Payload`](#payload)) |
| `timeout` | Optional per-request timeout |

An [`Auth.apply`](authentication.md#how-auth-is-applied) method receives a `Request`, mutates
its `headers` or `params`, and returns it.

## Response

The protocol-agnostic response your engine produces and your method consumes.

```python
@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
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

When an endpoint has no `response_model`, this `Response` is what Asas injects as your
method's first argument — call `response.json()` to read the body.

## Payload

A general container for request data, carried on `Request.payload`.

```python
@dataclass
class Payload:
    data: Optional[Any] = None
    json: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = {}
```

| Field | Meaning |
| --- | --- |
| `data` | Raw / form-encoded body |
| `json` | A JSON body — what Pydantic models are serialized into |
| `files` | File uploads |
| `headers` | Payload-specific headers |

When you pass a Pydantic model to an endpoint, Asas serializes it and stores the result in
`Payload.json`. See [Request Bodies & Responses](request-response.md) for how that routing
works.

!!! note "You rarely build these by hand"
    Asas constructs `Request` and `Payload` for you from your method call, and engines build
    `Response`. You work with these types directly mainly when writing a
    [custom engine](engines.md#writing-a-custom-engine) or a
    [custom auth strategy](authentication.md#how-auth-is-applied).
