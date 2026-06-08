
<p align="center">
  <a href="https://asas.dev"><img src="https://heshammoawad.github.io/asas-py/assets/logo-without-bg.png" alt="Asas"></a>
</p>

<p align="center">
    <em>Asas framework, high performance, easy to learn, fast to code, ready for production</em>
</p>

---
# Asas (API Client Builder)

## About

Asas is a streamlined framework designed for building API clients through a clean, decorator-based interface. Engineered for modern Python development, it provides native support for asynchronous operations and seamless integration with Pydantic for robust data validation.

## Goal

The core objective of Asas is to redefine API integration by making it more "Pythonic," elegant, and maintainable. By abstracting the verbosity typically associated with traditional request libraries, Asas empowers developers to focus on clear architecture and expressive code.

## Features

- **Sync & async clients** that share the same `@get`/`@post`/`@put`/`@delete`/`@patch` decorators.
- **Automatic parameter routing** — path placeholders, Pydantic-model bodies, and query parameters from one method signature.
- **Pydantic responses** via `response_model`.
- **Authentication** out of the box: `NoAuth`, `BasicAuth`, `BearerAuth`, `APIKeyAuth` (header/query/cookie), `RefreshingBearerAuth`, `OAuth2ClientCredentialsAuth`, `DigestAuth`, and `CompositeAuth`.
- **Transport-agnostic core** — `httpx` is the bundled engine; swap in your own.

## Documentation

Full docs (English + العربية): <https://heshammoawad.github.io/asas-py/>

- [Clients](docs/clients.md)
- [Routing & Parameters](docs/routing.md)
- [Request Bodies & Responses](docs/request-response.md)
- [Authentication](docs/authentication.md)
- [Engines & Transports](docs/engines.md)
- [Core Models](docs/models.md)
