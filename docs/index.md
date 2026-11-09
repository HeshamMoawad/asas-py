# Asas

<p align="center">
  <img src="https://heshammoawad.github.io/asas-py/assets/logo-without-bg.png" alt="Asas Logo" width="300">
</p>

<p align="center"><em>Asas framework, high performance, easy to learn, fast to code, ready for production</em></p>

---

## About

Asas is a streamlined framework for building **API clients (SDKs)** through a clean,
decorator-based interface. You subclass a client, annotate methods with `@get` / `@post` /
etc., and Asas handles request building, authentication, parsing, and retries for you.

It is engineered for modern Python: native `async`/`await` support and first-class
[Pydantic](https://docs.pydantic.dev/) integration for request and response validation.

## Goal

The core objective of Asas is to make API integration more **Pythonic**, simple, and
maintainable. By abstracting the verbosity of traditional request libraries, Asas lets you
focus on clear architecture and expressive code.

## Installation

```bash
pip install asas-py
```

## Quick start

Asas ships separate clients for synchronous and asynchronous code. The same decorators work
on both — Asas auto-detects `async def` methods.

=== "Synchronous"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyClient(AsasClient):
        @get("/users/{id}")
        def get_user(self, id: int) -> User:
            raise NotImplementedError

    with MyClient(base_url="https://api.example.com") as client:
        user = client.get_user(1)   # typed: User
    ```

=== "Asynchronous"

    ```python
    from pydantic import BaseModel

    from asas import AsasAsyncClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyAsyncClient(AsasAsyncClient):
        @get("/users/{id}")
        async def get_user(self, id: int) -> User:
            raise NotImplementedError

    async def main() -> None:
        async with MyAsyncClient(base_url="https://api.example.com") as client:
            user = await client.get_user(1)   # typed: User
    ```

!!! tip "The return annotation drives everything"
    The method body is **never executed** — write `raise NotImplementedError`. Asas reads the
    **return annotation** (`-> User`) to parse and validate the response, and the **parameters**
    to build the request. Callers see exactly the signature you declared, so type checkers and
    IDEs understand `client.get_user(1)`. See [Routing](routing.md) and
    [Parameters](parameters.md).

!!! info "Upgrading from 0.1?"
    Version 0.2 is a breaking release. See the [migration guide](migration-0.2.md).

## Feature highlights

- **[Clients](clients.md)** — sync and async clients with a swappable transport and
  runtime-settable auth.
- **[Routing](routing.md)** — `@get`/`@post`/`@put`/`@delete`/`@patch`, with the return
  annotation driving response parsing.
- **[Parameters](parameters.md)** — `Path`, `Query`, `Header`, `Cookie`, `Body`, `Form` and
  `File` markers, with aliases and inference when you omit them.
- **[Request bodies & responses](request-response.md)** — Pydantic models in, validated
  models out, typed from the return annotation.
- **[Errors](errors.md)** — non-2xx responses raise typed exceptions such as `NotFoundError`
  and `RateLimitError`.
- **[Hooks](hooks.md)** — observe or modify every request, response and error.
- **[Resources & pagination](resources.md)** — convention-driven CRUD and lazy iteration
  over every record, with no page-loop code.
- **[Authentication](authentication.md)** — Basic, Bearer, API key, automatic refresh, and
  composite strategies.
- **[Engines & transports](engines.md)** — a transport-agnostic core; `httpx` is the
  bundled reference engine, with an optional `requests` engine extra.
- **[Migration to 0.2](migration-0.2.md)** — before/after for every breaking change.
- **[Core models](models.md)** — plain `Request` / `Response` / `Payload` dataclasses that
  every layer speaks.
