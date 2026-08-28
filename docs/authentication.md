# Authentication

Authentication in Asas is a small, swappable strategy object. You pass one as `auth=` when
constructing a client, and it is applied to every request (unless an endpoint opts out with
[`use_auth=False`](routing.md#per-endpoint-auth-control)).

```python
from asas import AsasClient, BearerAuth

client = AsasClient(base_url="https://api.example.com", auth=BearerAuth("token"))
```

## Strategies at a glance

| Strategy | Use it for |
| --- | --- |
| [`NoAuth`](#noauth) | An explicit "no credentials" strategy |
| [`BasicAuth`](#basicauth) | HTTP Basic (`Authorization: Basic …`) |
| [`BearerAuth`](#bearerauth) | A static bearer token |
| [`APIKeyAuth`](#apikeyauth) | An API key in a header, query string, or cookie |
| [`RefreshingBearerAuth`](#refreshingbearerauth) | A bearer token that refreshes on `401` |
| [`CompositeAuth`](#compositeauth) | Combining several strategies at once |

## NoAuth

A no-op strategy. Useful as a readable, intentional alternative to `auth=None`.

```python
from asas import AsasClient, NoAuth

client = AsasClient(base_url="https://api.example.com", auth=NoAuth())
```

## BasicAuth

HTTP Basic authentication. Encodes `username:password` and sets the `Authorization` header.

```python
from asas import BasicAuth

auth = BasicAuth("username", "password")
# -> Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

## BearerAuth

A static bearer token.

```python
from asas import BearerAuth

auth = BearerAuth("my-secret-token")
# -> Authorization: Bearer my-secret-token
```

## APIKeyAuth

An API key sent in a header (default), query string, or cookie. The location is chosen with
the `APIKeyLocation` enum; a plain `"header"` / `"query"` / `"cookie"` string is also
accepted.

=== "Header (default)"

    ```python
    from asas import APIKeyAuth

    auth = APIKeyAuth("secret-key", name="X-API-Key")
    # -> X-API-Key: secret-key
    ```

=== "Query string"

    ```python
    from asas import APIKeyAuth, APIKeyLocation

    auth = APIKeyAuth("secret-key", name="api_key", location=APIKeyLocation.QUERY)
    # -> ...?api_key=secret-key
    ```

=== "Cookie"

    ```python
    from asas import APIKeyAuth, APIKeyLocation

    auth = APIKeyAuth("secret-key", name="session", location=APIKeyLocation.COOKIE)
    # -> Cookie: session=secret-key
    ```

`APIKeyLocation` has three members: `HEADER`, `QUERY`, and `COOKIE`. Passing an unknown
location string raises `ValueError`.

## RefreshingBearerAuth

A bearer token that **refreshes itself on a `401`**. When a request comes back unauthorized,
Asas calls your refresh callback, rebuilds the request with the new token, and retries it
**exactly once**.

=== "Synchronous"

    ```python
    from asas import AsasClient, RefreshingBearerAuth

    def fetch_new_token() -> str:
        # Call your auth server here and return the fresh token.
        return "new-token"

    auth = RefreshingBearerAuth("initial-token", refresh_callback=fetch_new_token)
    client = AsasClient(base_url="https://api.example.com", auth=auth)
    ```

=== "Asynchronous"

    ```python
    from asas import AsasAsyncClient, RefreshingBearerAuth

    async def fetch_new_token() -> str:
        return "new-token"

    auth = RefreshingBearerAuth("initial-token", async_refresh_callback=fetch_new_token)
    client = AsasAsyncClient(base_url="https://api.example.com", auth=auth)
    ```

You can customize the header and prefix with `key_name=` and `token_prefix=` (defaults:
`"Authorization"` and `"Bearer "`).

!!! note "Retry limit"
    The refresh-and-retry happens at most once per call. If the retried request also returns
    `401`, that response is returned as-is.

## Customizing when a refresh happens

By default a refresh fires only on an HTTP `401`. Many APIs signal an expired token
differently — a `200` with an error code in the body, a keyword in the payload, or a
non-standard status. Pass a `refresh_when` condition to override *when* the refresh-and-retry
runs. This works on `RefreshingBearerAuth`.

A condition is just a `Callable[[Response], bool]`. Asas ships builders for the common cases
(import them from `asas`):

| Builder | Refreshes when… |
| --- | --- |
| `refresh_on_status(*codes)` | the status is one of `codes` (the default is `401`) |
| `refresh_on_keyword(keyword)` | `keyword` appears anywhere in the response body |
| `refresh_on_json(key, value=…, status=…)` | the JSON body has `key` (optionally `== value`, optionally at a given status) |
| `refresh_on_any(*conditions)` | any of the conditions is true |
| `refresh_on_all(*conditions)` | all of the conditions are true |

=== "Keyword in the body"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_keyword

    # Refresh when the response body contains "token_expired" (even on a 200).
    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_keyword("token_expired"),
    )
    ```

=== "200 with a body key/value"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_json

    # Refresh when the API replies 200 but the body says the token expired.
    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_json("code", "AUTH_EXPIRED", status=200),
    )
    ```

=== "Custom status"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_status

    # Some APIs use 419/440 for an expired session instead of 401.
    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_status(419, 440),
    )
    ```

=== "Combine conditions"

    ```python
    from asas import RefreshingBearerAuth, refresh_on_any, refresh_on_status, refresh_on_keyword

    auth = RefreshingBearerAuth(
        "token",
        refresh_callback=get_new_token,
        refresh_when=refresh_on_any(refresh_on_status(401), refresh_on_keyword("expired")),
    )
    ```

`refresh_on_json` accepts a dotted `key` for nested bodies (e.g. `"error.code"`).

For full control, subclass the auth and override `should_refresh(response) -> bool`:

```python
class HeaderRefreshAuth(RefreshingBearerAuth):
    def should_refresh(self, response):
        # Response header names are lowercased.
        return response.headers.get("x-token-expired") == "1"
```

!!! note "Custom auth strategies are unaffected"
    The condition is read from an optional `should_refresh` method. An auth strategy that
    only implements `refresh` / `arefresh` keeps the default `401` behaviour.

## CompositeAuth

Apply several strategies to one request, in order — handy when an API needs more than one
credential at once (for example an API key **and** a bearer token):

```python
from asas import AsasClient, CompositeAuth, APIKeyAuth, BearerAuth

auth = CompositeAuth(
    APIKeyAuth("key-123", name="X-API-Key"),
    BearerAuth("token-abc"),
)
client = AsasClient(base_url="https://api.example.com", auth=auth)
# -> X-API-Key: key-123  AND  Authorization: Bearer token-abc
```

Refresh and challenge handling are delegated to any members that support them, so a
`CompositeAuth` containing a `RefreshingBearerAuth` still refreshes on `401`.

## How auth is applied

Every strategy implements the `Auth` protocol — a single `apply(request) -> request` method
that mutates headers or query params. Two protocols extend it:

- **`RefreshableAuth`** adds `refresh()` / `arefresh()`, called on a `401` to renew
  credentials before one retry.
- **`ChallengeResponseAuth`** adds `handle_challenge(response) -> bool`, called on a `401` so
  a scheme can read the server's challenge before retrying.

To build your own scheme, implement `apply` (and optionally one of the two protocols above):

```python
from asas.auth import Auth
from asas.core.models import Request

class HeaderAuth(Auth):
    def __init__(self, header: str, value: str) -> None:
        self.header = header
        self.value = value

    def apply(self, request: Request) -> Request:
        request.headers[self.header] = self.value
        return request
```

See [Core Models](models.md) for the `Request` shape your `apply` method receives.
