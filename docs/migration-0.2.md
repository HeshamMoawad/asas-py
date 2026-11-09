# Migrating to 0.2

Asas 0.2.0 is a breaking release. The core idea is that a decorated method is now declared
like a typed function — the **return annotation** drives parsing and the **parameters** drive
the request — so callers get correct types. This page shows a before/after pair for each
breaking change.

## 1. Endpoint bodies no longer receive the parsed result

In 0.1 the parsed result was injected as the first argument after `self`. In 0.2 nothing is
injected, the body is never executed, and the return annotation says what you get back.

=== "0.1"

    ```python
    @get("/users/{id}", response_model=User)
    def get_user(self, user: User, id: int) -> User:
        return user

    client.get_user(id=1)
    ```

=== "0.2"

    ```python
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError

    client.get_user(1)
    ```

To post-process a result, write an ordinary method that calls the endpoint, or use a
[hook](hooks.md). For the raw response, annotate `-> Response`.

=== "0.1"

    ```python
    @get("/users/{id}")
    def get_username(self, response: Response, id: int) -> str:
        return response.json()["name"]
    ```

=== "0.2"

    ```python
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError

    def get_username(self, id: int) -> str:
        return self.get_user(id).name
    ```

Write `raise NotImplementedError` as the body: `mypy --strict` rejects a bare `...` with
`[empty-body]`.

## 2. `response_model=` is removed

=== "0.1"

    ```python
    @get("/users", response_model=List[User])
    def get_users(self, users: List[User]) -> List[User]:
        return users
    ```

=== "0.2"

    ```python
    @get("/users")
    def get_users(self) -> list[User]:
        raise NotImplementedError
    ```

A missing return annotation is a `TypeError`.

## 3. Non-2xx responses raise by default

=== "0.1"

    ```python
    data = client.get_user(id=404)      # returned the error body, silently
    ```

=== "0.2"

    ```python
    from asas import NotFoundError

    try:
        user = client.get_user(404)
    except NotFoundError:
        user = None
    ```

Opt out per client with `AsasClient(raise_for_status=False)`, per endpoint with
`@get(..., raise_for_status=False)`, or by returning `Response`. See [Errors](errors.md).

Resource iteration is the exception: a `404` on a page after the first ends iteration without
raising, as in 0.1, because DRF and similar APIs answer `404` past the last page. See
[Lazy iteration](resources.md#lazy-iteration-over-every-record).

## 4. Parameter routing comes from annotations

Routing is decided from the annotations at decoration time, not from the runtime values.
Unannotated `dict` parameters now go to the **body**, not the query string. Use
[markers](parameters.md) for explicit control.

=== "0.1"

    ```python
    @get("/search")
    def search(self, response: Response, filters: dict):
        ...                       # `filters` was sent as query parameters
    ```

=== "0.2"

    ```python
    @get("/search")
    def search(self, status: str, limit: int = 10) -> dict:
        raise NotImplementedError   # scalars go to the query: ?status=...&limit=10
    ```

A `dict` value is **not** expanded into query keys: annotated as `Query()` it would be sent as
one stringified value. To send several query keys, declare each as its own scalar parameter
(as above). Every parameter must now have a type annotation.

## 5. Python 3.9 is dropped

=== "0.1"

    ```toml
    requires-python = ">=3.9"
    ```

=== "0.2"

    ```toml
    requires-python = ">=3.10"
    ```

Asas 0.2 supports Python 3.10 to 3.13, which also lets you write `str | None` and
`list[User]` in annotations.

## 6. Client constructor arguments after `base_url` are keyword-only

=== "0.1"

    ```python
    client = MyClient("https://api.example.com", engine, auth)
    ```

=== "0.2"

    ```python
    client = MyClient("https://api.example.com", engine=engine, auth=auth)
    ```

## 7. `Resource.delete()` returns `None`

Resources are also generic over their model now, and raise `ResponseValidationError` (not a
raw Pydantic `ValidationError`) when a record or page fails validation.

=== "0.1"

    ```python
    class Users(AsasResource):
        path = "/users"
        model = User

    response = client.users.delete(1)     # a Response
    ```

=== "0.2"

    ```python
    class Users(AsasResource[User]):
        path = "/users"

    client.users.delete(1)                # None; raises on a non-2xx status
    ```

Code that caught `pydantic.ValidationError` around resource calls should catch
`asas.ResponseValidationError` (its `.error` attribute holds the original exception).

## 8. `APIKeyAuth` in a cookie uses `Request.cookies`

=== "0.1"

    ```python
    # wrote a raw `Cookie: session=...` header
    request.headers["Cookie"]
    ```

=== "0.2"

    ```python
    # writes to the new cookies field, which engines send
    request.cookies["session"]
    ```

## 9. Custom engines must raise `TransportError` and send cookies

=== "0.1"

    ```python
    def send(self, request: Request) -> Response:
        resp = self.session.request(request.method, request.url, headers=request.headers)
        return Response(resp.status_code, dict(resp.headers), resp.content, resp.text)
    ```

=== "0.2"

    ```python
    def send(self, request: Request) -> Response:
        try:
            resp = self.session.request(
                request.method,
                request.url,
                headers=request.headers,
                cookies=request.cookies,
                timeout=request.timeout,
            )
        except requests.RequestException as exc:
            raise TransportError(str(exc), request) from exc
        return Response(resp.status_code, dict(resp.headers), resp.content, resp.text)
    ```

See [the engine contract](engines.md#the-engine-contract).

## Smaller fixes you get for free

- Path values are percent-encoded (`quote(str(v), safe="")`), and so are resource ids in
  `get` / `update` / `delete`.
- Request bodies are dumped JSON-safe and by alias (`datetime`, `UUID`, `Decimal`, enums).
- The default engine applies client defaults: `AsasClient(headers=..., timeout=...)` now takes
  effect. Previously these were silently dropped.
- `Payload.json` is typed `Any`.
- Clients are context managers and have `close()` / `aclose()`.
