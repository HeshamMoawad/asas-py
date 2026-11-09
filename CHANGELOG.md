# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - Unreleased

A breaking release. See the [migration guide](docs/migration-0.2.md).

### Breaking

- Endpoint bodies no longer receive the parsed result; the **return annotation** drives
  parsing and the method body is never executed (write `raise NotImplementedError`).
- `response_model=` is removed; use the return annotation.
- Non-2xx responses raise a typed `HTTPStatusError` subclass by default
  (`raise_for_status` on the client or endpoint; `-> Response` endpoints never raise).
  Resource iteration is the exception: a `404` on a page after the first ends iteration
  without raising or calling `on_error`, as DRF and similar APIs answer `404` past the end.
- Parameter routing is decided from annotations, not runtime values; unannotated `dict`
  parameters now go to the JSON body instead of the query string, and every parameter needs
  an annotation.
- Python 3.9 is dropped; Asas requires Python 3.10 or newer.
- Client constructor arguments after `base_url` are keyword-only.
- `Resource.delete()` returns `None` instead of `Response`.
- Resources raise `ResponseValidationError` instead of a raw Pydantic `ValidationError` when a
  record or page fails validation.
- `APIKeyAuth` with `APIKeyLocation.COOKIE` writes to `Request.cookies` instead of a raw
  `Cookie` header.
- Custom engines must wrap transport exceptions in `TransportError` and send
  `Request.cookies`.

### Added

- Parameter markers `Path`, `Query`, `Header`, `Cookie`, `Body`, `Form` and `File`, with
  aliases, inference from annotations, and compile-time `TypeError`s for declaration mistakes.
- Form-encoded and multipart bodies.
- A typed error hierarchy: `AsasError`, `HTTPStatusError`, `ClientError`, `ServerError`,
  `BadRequestError`, `UnauthorizedError`, `ForbiddenError`, `NotFoundError`,
  `ConflictError`, `UnprocessableEntityError`, `RateLimitError` (with `retry_after`),
  `InternalServerError`, `ServiceUnavailableError`, `ResponseValidationError` and
  `TransportError`.
- `Hooks` (`on_request`, `on_response`, `on_error`) on clients and endpoints.
- `headers`, `timeout`, `raise_for_status` and `hooks` arguments on the request decorators,
  and `raise_for_status` and `hooks` arguments on the clients.
- Endpoints whose types are not defined yet at decoration time are compiled on their first
  call (declaration `TypeError`s for them surface then rather than at import).
- `close()` / `aclose()` and `with` / `async with` support on clients.
- Generic resources (`AsasResource[User]`, `AsasAsyncResource[User]`) with model inference;
  CRUD runs through the shared request pipeline, so it raises typed errors and fires hooks.
- `Request.cookies`, and `Payload.data` accepting form fields or raw bytes.
- Documentation: Parameters, Errors, Hooks and the 0.2 migration guide (English and Arabic).

### Fixed

- Path values and resource ids (`get` / `update` / `delete`) are percent-encoded.
- Request bodies are dumped JSON-safe and by alias (`datetime`, `UUID`, `Decimal`, enums).
- The httpx engine honours per-request timeouts, and applies client defaults:
  `AsasClient(headers=..., timeout=...)` engine kwargs were previously silently dropped.
- `Payload.json` is typed `Any` instead of `Dict[str, Any]`.
- Cookie-based API key auth sends a real cookie through the engines.

## [0.1.0] - 2026-08-29

### Added

- Initial release of **Asas**, a typed, elegant Python API client builder.
- Core client layer with sync and async variants (`AsasClient` / `AsasAsyncClient`)
  and auto-detection of `async def` methods — one decorator set drives both.
- HTTP method decorators: `@get`, `@post`, `@put`, `@delete`, `@patch`.
- Automatic parameter routing from a single method signature:
  path placeholders become URL segments, Pydantic models become JSON bodies,
  and any other param becomes a query string.
- Pydantic request/response validation via `response_model` (`TypeAdapter`).
- Transport-agnostic core (`Request` / `Response` / `Payload` models)
  with an httpx engine for sync and async transport.
- Authentication support: `NoAuth`, `BasicAuth`, `BearerAuth`, `APIKeyAuth`
  (header / query / cookie via `APIKeyLocation`), `RefreshingBearerAuth`, and
  `CompositeAuth`.
- Automatic token refresh with `401` retry, plus a `use_auth` parameter to
  disable auth per endpoint and a settable `auth` property for runtime swapping.
- Customizable refresh conditions (`RefreshCondition`, `refresh_on_status`,
  `refresh_on_keyword`, `refresh_on_json`, `refresh_on_any`, `refresh_on_all`)
  and challenge-response auth (`ChallengeResponseAuth`).
- Convention-driven Resources (`AsasResource` / `AsasAsyncResource`) with
  generated CRUD (`list` / `get` / `create` / `update` / `delete`) and lazy
  pagination via an iterator — no page-loop code required.
- Built-in paginators: page-number, offset, cursor, and Link-header.
- Optional sync-only `requests` engine behind the `[requests]` extra.
- Bilingual documentation (English + Arabic) with runnable examples.
- A contributing workflow (`CONTRIBUTING.md`) and make-based tooling
  (`make dev-install`, `format`, `lint`, `test`, `build`, `docs-serve`).

[Unreleased]: https://github.com/HeshamMoawad/asas-py/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/HeshamMoawad/asas-py/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/HeshamMoawad/asas-py/releases/tag/v0.1.0
