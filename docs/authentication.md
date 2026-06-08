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
| [`OAuth2ClientCredentialsAuth`](#oauth2clientcredentialsauth) | The OAuth2 client-credentials grant |
| [`DigestAuth`](#digestauth) | HTTP Digest challenge/response |
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

## OAuth2ClientCredentialsAuth

Implements the OAuth2 **client-credentials** grant. It mints a bearer token from your token
endpoint and refreshes it on a `401`. The first protected call triggers the token request
automatically.

```python
from asas import AsasClient, OAuth2ClientCredentialsAuth

auth = OAuth2ClientCredentialsAuth(
    token_url="https://auth.example.com/oauth/token",
    client_id="my-client-id",
    client_secret="my-client-secret",
    scope="read write",   # optional
)
client = AsasClient(base_url="https://api.example.com", auth=auth)
```

By default the token request is performed with `httpx` (a `POST` of
`grant_type=client_credentials`). To route it through a different transport, pass a
`token_fetcher` (sync) or `async_token_fetcher` (async). Each receives the form fields and
returns either the access-token string or a `{"access_token": ..., "expires_in": ...}`
mapping:

```python
def fetch(form: dict) -> dict:
    resp = my_http_lib.post("https://auth.example.com/oauth/token", data=form)
    return resp.json()   # {"access_token": "...", "expires_in": 3600}

auth = OAuth2ClientCredentialsAuth(
    token_url="https://auth.example.com/oauth/token",
    client_id="id",
    client_secret="secret",
    token_fetcher=fetch,
)
```

When the token response includes `expires_in`, the `is_expired` property reflects it.

## DigestAuth

HTTP Digest authentication (RFC 7616), handled as a challenge/response:

1. The first request is sent **without** credentials.
2. The server replies `401` with a `WWW-Authenticate: Digest …` challenge.
3. Asas feeds the challenge back to the strategy, rebuilds the request with the computed
   digest, and retries it once.

```python
from asas import AsasClient, DigestAuth

auth = DigestAuth("username", "password")
client = AsasClient(base_url="https://api.example.com", auth=auth)
```

Supports `qop=auth` and the `MD5` and `SHA-256` algorithms. Subsequent requests reuse the
cached challenge with an incrementing nonce count.

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
  schemes like Digest can read the server's challenge before retrying.

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
