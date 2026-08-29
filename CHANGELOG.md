# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/HeshamMoawad/asas-py/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HeshamMoawad/asas-py/releases/tag/v0.1.0
