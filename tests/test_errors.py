from datetime import datetime, timezone
from typing import Dict, List, Optional

import pytest
import respx
from httpx import Response as HttpxResponse
from pydantic import BaseModel

from asas import (
    AsasAsyncClient,
    AsasClient,
    Hooks,
    RefreshingBearerAuth,
    Request,
    Response,
    get,
)
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


@pytest.mark.parametrize("value,expected", [("-5", 0.0), ("inf", None), ("nan", None)])
def test_retry_after_negative_clamped_and_non_finite_rejected(
    value: str, expected: Optional[float]
) -> None:
    assert parse_retry_after(value) == expected


def test_retry_after_lowercase_header_key() -> None:
    # httpx's dict(response.headers) lowercases keys: the production path.
    err = error_for_response(req, resp(429, headers={"retry-after": "3"}))
    assert isinstance(err, RateLimitError) and err.retry_after == 3.0


def test_rate_limit_without_retry_after_header() -> None:
    err = error_for_response(req, resp(429))
    assert isinstance(err, RateLimitError) and err.retry_after is None


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


# --- Pipeline status handling (through decorated clients) ------------------

BASE = "https://api.example.com"


class User(BaseModel):
    id: int


class StatusClient(AsasClient):
    @get("/u/{id}")
    def user(self, id: int) -> User:
        ...

    @get("/maybe/{id}")
    def maybe_user(self, id: int) -> Optional[User]:
        ...

    @get("/raw")
    def raw(self) -> Response:
        ...

    @get("/fire")
    def fire(self) -> None:
        ...

    @get("/strict", raise_for_status=True)
    def strict(self) -> None:
        ...


class AsyncStatusClient(AsasAsyncClient):
    @get("/u/{id}")
    async def user(self, id: int) -> User:
        ...


def test_raises_not_found_by_default() -> None:
    client = StatusClient(BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/u/1").mock(return_value=HttpxResponse(404))
        with pytest.raises(NotFoundError) as exc:
            client.user(1)
    assert exc.value.request.url == f"{BASE}/u/1"


@pytest.mark.asyncio
async def test_raises_not_found_by_default_async() -> None:
    client = AsyncStatusClient(BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/u/1").mock(return_value=HttpxResponse(404))
        with pytest.raises(NotFoundError):
            await client.user(1)
    await client.engine.aclose()


def test_optional_return_still_raises_on_404() -> None:
    client = StatusClient(BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/maybe/1").mock(return_value=HttpxResponse(404))
        with pytest.raises(NotFoundError):
            client.maybe_user(1)


def test_response_return_never_raises() -> None:
    errors: List[AsasError] = []
    client = StatusClient(BASE, hooks=Hooks(on_error=[errors.append]))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/raw").mock(return_value=HttpxResponse(500))
        result = client.raw()
    assert isinstance(result, Response) and result.status_code == 500
    assert errors == []


def test_raise_for_status_resolution() -> None:
    client = StatusClient(BASE, raise_for_status=False)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/fire").mock(return_value=HttpxResponse(500))
        mock.get("/strict").mock(return_value=HttpxResponse(500))
        assert client.fire() is None
        with pytest.raises(ServerError):
            client.strict()


def test_status_error_raised_after_refresh_retry() -> None:
    auth = RefreshingBearerAuth("old", refresh_callback=lambda: "new")
    client = StatusClient(BASE, auth=auth)
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/u/1").mock(return_value=HttpxResponse(401))
        with pytest.raises(UnauthorizedError) as exc:
            client.user(1)
    assert route.call_count == 2
    assert exc.value.request.headers["Authorization"] == "Bearer new"
