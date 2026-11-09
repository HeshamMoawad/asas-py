from datetime import datetime, timezone
from typing import Dict, Optional

import pytest

from asas import Request, Response
from asas.errors import (
    AsasError,
    BadRequestError,
    ClientError,
    ConflictError,
    ForbiddenError,
    HTTPStatusError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    ResponseValidationError,
    ServerError,
    ServiceUnavailableError,
    TransportError,
    UnauthorizedError,
    UnprocessableEntityError,
    error_for_response,
    parse_retry_after,
)

req = Request("GET", "https://api.example.com/x")


def resp(
    status: int, content: bytes = b"", headers: Optional[Dict[str, str]] = None
) -> Response:
    return Response(status, headers or {}, content, content.decode("utf-8", "replace"))


@pytest.mark.parametrize(
    "status,cls",
    [
        (400, BadRequestError),
        (401, UnauthorizedError),
        (403, ForbiddenError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, UnprocessableEntityError),
        (429, RateLimitError),
        (500, InternalServerError),
        (503, ServiceUnavailableError),
        (418, ClientError),
        (502, ServerError),
        (302, HTTPStatusError),
    ],
)
def test_error_for_response_picks_most_specific_class(status, cls):  # type: ignore[no-untyped-def]
    err = error_for_response(req, resp(status))
    assert type(err) is cls and err.status_code == status
    assert err.request is req and err.response.status_code == status


def test_message_format() -> None:
    err = error_for_response(
        Request("GET", "https://api.example.com/users/1"),
        resp(404, b'{"detail":"nope"}'),
    )
    assert (
        str(err)
        == 'GET https://api.example.com/users/1 → 404 Not Found: {"detail":"nope"}'
    )


def test_message_truncates_and_survives_binary_body() -> None:
    err = error_for_response(req, resp(502, b"\xff\xfe" + b"x" * 500))
    body_part = str(err).split(": ", 1)[1]
    assert len(body_part) == 200


def test_retry_after_seconds() -> None:
    err = error_for_response(req, resp(429, headers={"Retry-After": "7"}))
    assert isinstance(err, RateLimitError) and err.retry_after == 7.0


def test_retry_after_http_date() -> None:
    now = datetime(2026, 11, 9, 12, 0, 0, tzinfo=timezone.utc)
    assert parse_retry_after("Mon, 09 Nov 2026 12:00:30 GMT", now=now) == 30.0
    assert parse_retry_after("Mon, 09 Nov 2026 11:00:00 GMT", now=now) == 0.0


def test_retry_after_missing_or_garbage() -> None:
    assert parse_retry_after(None) is None
    assert parse_retry_after("soon") is None


def test_hierarchy_and_exports() -> None:
    assert issubclass(NotFoundError, ClientError)
    assert issubclass(ClientError, HTTPStatusError)
    assert issubclass(HTTPStatusError, AsasError)
    assert issubclass(TransportError, AsasError)
    assert issubclass(ResponseValidationError, AsasError)
    import asas

    for name in [
        "AsasError",
        "HTTPStatusError",
        "ClientError",
        "ServerError",
        "BadRequestError",
        "UnauthorizedError",
        "ForbiddenError",
        "NotFoundError",
        "ConflictError",
        "UnprocessableEntityError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
        "TransportError",
        "ResponseValidationError",
    ]:
        assert name in asas.__all__
        assert hasattr(asas, name)
