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

The core objective of Asas is to make API integration more **Pythonic**, elegant, and
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
    from asas import AsasClient, get, Response

    class MyClient(AsasClient):
        @get("/users/{id}")
        def get_user(self, response: Response, id: int):
            return response.json()

    client = MyClient(base_url="https://api.example.com")
    user = client.get_user(id=1)
    ```

=== "Asynchronous"

    ```python
    from asas import AsasAsyncClient, get, Response

    class MyAsyncClient(AsasAsyncClient):
        @get("/users/{id}")
        async def get_user(self, response: Response, id: int):
            return response.json()

    async def main():
        client = MyAsyncClient(base_url="https://api.example.com")
        user = await client.get_user(id=1)
        await client.engine.aclose()
    ```

!!! tip "The injected first argument"
    The decorated method receives the parsed result as its **first argument after `self`**
    (`response` above). Any remaining parameters — like `id` — are supplied by the caller
    and routed into the request. See [Routing & Parameters](routing.md).

## Feature highlights

- **[Clients](clients.md)** — sync and async clients with a swappable transport and
  runtime-settable auth.
- **[Routing & Parameters](routing.md)** — `@get`/`@post`/`@put`/`@delete`/`@patch` with
  automatic path, query, and body routing.
- **[Request bodies & responses](request-response.md)** — Pydantic models in, validated
  models out via `response_model`.
- **[Resources & pagination](resources.md)** — convention-driven CRUD and lazy iteration
  over every record, with no page-loop code.
- **[Authentication](authentication.md)** — Basic, Bearer, API key, automatic refresh, and
  composite strategies.
- **[Engines & transports](engines.md)** — a transport-agnostic core; `httpx` is the
  bundled reference engine, with an optional `requests` engine extra.
- **[Core models](models.md)** — plain `Request` / `Response` / `Payload` dataclasses that
  every layer speaks.
