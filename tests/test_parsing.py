from __future__ import annotations

from typing import Any, Callable

import pydantic
import pytest
from pydantic import BaseModel

from asas.core.models import Response
from asas.endpoint import EndpointOptions, EndpointSpec
from asas.errors import ResponseValidationError


class User(BaseModel):
    id: int
    name: str


def resp(status: int, content: bytes) -> Response:
    return Response(
        status_code=status, headers={}, content=content, text=content.decode()
    )


def spec_for(func: Callable[..., Any]) -> EndpointSpec:
    return EndpointSpec.compile("GET", "/x", func, EndpointOptions())


def f_response(self: Any) -> Response:
    raise NotImplementedError


def f_none(self: Any) -> None:
    raise NotImplementedError


def f_bytes(self: Any) -> bytes:
    raise NotImplementedError


def f_str(self: Any) -> str:
    raise NotImplementedError


def f_user(self: Any) -> User:
    raise NotImplementedError


def f_list(self: Any) -> list[User]:
    raise NotImplementedError


def f_opt(self: Any) -> User | None:
    raise NotImplementedError


def test_response_kind_returns_raw() -> None:
    r = resp(200, b"x")
    assert spec_for(f_response).parse_response(r) is r


def test_none_kind_returns_none() -> None:
    assert spec_for(f_none).parse_response(resp(200, b"x")) is None


def test_bytes_and_str_kinds() -> None:
    r = resp(200, b"hi")
    assert spec_for(f_bytes).parse_response(r) == b"hi"
    assert spec_for(f_str).parse_response(r) == "hi"


def test_model_kind_validates() -> None:
    out = spec_for(f_user).parse_response(resp(200, b'{"id":1,"name":"Ada"}'))
    assert out == User(id=1, name="Ada")


def test_list_model() -> None:
    out = spec_for(f_list).parse_response(resp(200, b'[{"id":1,"name":"Ada"}]'))
    assert out == [User(id=1, name="Ada")]


def test_empty_body_optional_returns_none() -> None:
    assert spec_for(f_opt).parse_response(resp(204, b"  ")) is None


def test_empty_body_required_raises() -> None:
    with pytest.raises(ResponseValidationError):
        spec_for(f_user).parse_response(resp(200, b""))


def test_invalid_json_raises_response_validation_error() -> None:
    with pytest.raises(ResponseValidationError) as exc:
        spec_for(f_user).parse_response(resp(200, b"<html>"))
    assert exc.value.response.content == b"<html>"


def test_schema_mismatch_wraps_pydantic_error() -> None:
    with pytest.raises(ResponseValidationError) as exc:
        spec_for(f_user).parse_response(resp(200, b'{"id":"x"}'))
    assert isinstance(exc.value.error, pydantic.ValidationError)


def f_opt_str(self: Any) -> str | None:
    raise NotImplementedError


def f_opt_bytes(self: Any) -> bytes | None:
    raise NotImplementedError


@pytest.mark.parametrize(
    "func,body,expected",
    [
        (f_opt_str, b"plain text", "plain text"),
        (f_opt_str, b"", None),
        (f_opt_bytes, b"\x00raw", b"\x00raw"),
        (f_opt_bytes, b"", None),
    ],
)
def test_optional_str_and_bytes(
    func: Callable[..., Any], body: bytes, expected: Any
) -> None:
    r = Response(
        status_code=200,
        headers={"content-type": "text/plain"},
        content=body,
        text=body.decode("latin-1"),
    )
    assert spec_for(func).parse_response(r) == expected
