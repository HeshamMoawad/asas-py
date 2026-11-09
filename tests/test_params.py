from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Callable, Optional
from uuid import UUID

import pytest
from pydantic import BaseModel, Field

from asas.core.models import Request
from asas.endpoint import EndpointOptions, EndpointSpec, dump_body
from asas.params import Body, Cookie, File, Form, Header, Location, Path, Query


def test_marker_locations() -> None:
    assert Path().location is Location.PATH and Query().location is Location.QUERY
    assert Header().location is Location.HEADER
    assert Cookie().location is Location.COOKIE
    assert Body().location is Location.BODY and Form().location is Location.FORM
    assert File().location is Location.FILE


def test_header_alias_positional_others_keyword_only() -> None:
    assert Header("X-Trace").alias == "X-Trace"
    assert Query(alias="pageSize").alias == "pageSize"
    with pytest.raises(TypeError):
        Query("pageSize")  # type: ignore[misc]


def test_body_options() -> None:
    b = Body(exclude_unset=True)
    assert b.exclude_unset and not b.exclude_none and b.alias is None
    with pytest.raises(TypeError):
        Body("x")  # type: ignore
    with pytest.raises(TypeError):
        Body(alias="x")  # type: ignore


def test_markers_exported() -> None:
    import asas

    assert {"Path", "Query", "Header", "Cookie", "Body", "Form", "File"} <= set(
        asas.__all__
    )


BASE = "https://api.test"


class Color(str, Enum):
    RED = "red"


class Item(BaseModel):
    uid: UUID
    amount: Decimal
    created: datetime
    name: str = Field(alias="displayName")


class Patch(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None


class Person(BaseModel):
    id: int


def build(
    func: Callable[..., Any],
    args: tuple[Any, ...] = (),
    kwargs: Optional[dict[str, Any]] = None,
    path: str = "/x",
    **opts: Any,
) -> Request:
    spec = EndpointSpec.compile("POST", path, func, EndpointOptions(**opts))
    return spec.build_request(BASE, args, kwargs or {})


def test_path_value_is_url_encoded() -> None:
    def f(self: Any, id: str) -> None:
        ...

    assert build(f, ("a/b c",), path="/items/{id}").url == f"{BASE}/items/a%2Fb%20c"


def test_path_alias_substitution() -> None:
    def f(self: Any, user_id: Annotated[int, Path(alias="userId")]) -> None:
        ...

    assert build(f, (5,), path="/users/{userId}").url == f"{BASE}/users/5"


def test_query_alias_list_bool_enum_datetime() -> None:
    def f(
        self: Any,
        page_size: Annotated[int, Query(alias="pageSize")] = 10,
        tags: Optional[list[str]] = None,
        active: bool = False,
        color: Optional[Color] = None,
        since: Optional[datetime] = None,
    ) -> None:
        ...

    req = build(
        f,
        kwargs={
            "tags": ["a", "b"],
            "active": True,
            "color": Color.RED,
            "since": datetime(2026, 1, 2, 3, 4, 5),
        },
    )
    assert req.params == {
        "pageSize": "10",
        "tags": ["a", "b"],
        "active": "true",
        "color": "red",
        "since": "2026-01-02T03:04:05",
    }


def test_none_values_omitted() -> None:
    def f(
        self: Any,
        q: Optional[str] = None,
        h: Annotated[Optional[str], Header()] = None,
        c: Annotated[Optional[str], Cookie()] = None,
        fm: Annotated[Optional[str], Form()] = None,
    ) -> None:
        ...

    req = build(f)
    assert not req.params and not req.headers and not req.cookies
    assert req.payload is None or not req.payload.data


def test_none_path_value_raises_value_error() -> None:
    def f(self: Any, id: Optional[int]) -> None:
        ...

    with pytest.raises(ValueError, match="id"):
        build(f, (None,), path="/i/{id}")


def test_body_is_json_safe_and_aliased() -> None:
    def f(self: Any, item: Item) -> None:
        ...

    item = Item(
        uid=UUID(int=1),
        amount=Decimal("1.50"),
        created=datetime(2026, 1, 2, 3, 4, 5),
        displayName="Ada",
    )
    req = build(f, (item,))
    assert req.payload is not None
    assert req.payload.json == {
        "uid": str(UUID(int=1)),
        "amount": "1.50",
        "created": "2026-01-02T03:04:05",
        "displayName": "Ada",
    }


def test_body_exclude_unset() -> None:
    def f(self: Any, p: Annotated[Patch, Body(exclude_unset=True)]) -> None:
        ...

    req = build(f, (Patch(name="x"),))
    assert req.payload is not None and req.payload.json == {"name": "x"}


def test_list_body() -> None:
    def f(self: Any, users: list[Person]) -> None:
        ...

    req = build(f, ([Person(id=1), Person(id=2)],))
    assert req.payload is not None
    assert req.payload.json == [{"id": 1}, {"id": 2}]


def test_form_only() -> None:
    def f(self: Any, a: Annotated[int, Form()]) -> None:
        ...

    req = build(f, (1,))
    assert req.payload is not None
    assert req.payload.data == {"a": "1"} and req.payload.files is None


def test_form_and_file() -> None:
    def f(
        self: Any,
        note: Annotated[str, Form()],
        file: Annotated[bytes, File()],
    ) -> None:
        ...

    req = build(f, ("hi", b"bytes"))
    assert req.payload is not None
    assert req.payload.data == {"note": "hi"}
    assert req.payload.files == {"file": b"bytes"}


def test_cookie() -> None:
    def f(self: Any, session: Annotated[str, Cookie()]) -> None:
        ...

    assert build(f, ("s",)).cookies == {"session": "s"}


def test_header_precedence() -> None:
    def f(self: Any, b: Annotated[str, Header("X-B")]) -> None:
        ...

    req = build(f, ("2",), headers={"X-A": "1", "X-B": "1"})
    assert req.headers == {"X-A": "1", "X-B": "2"}


def test_timeout_from_options() -> None:
    def f(self: Any) -> None:
        ...

    assert build(f, timeout=3.0).timeout == 3.0


def test_missing_required_argument_raises_type_error() -> None:
    def f(self: Any, a: int) -> None:
        ...

    with pytest.raises(TypeError):
        build(f)


def test_unknown_keyword_raises_type_error() -> None:
    def f(self: Any, a: int) -> None:
        ...

    with pytest.raises(TypeError):
        build(f, (1,), {"nope": 2})


def test_dump_body_without_adapter() -> None:
    item = Item(
        uid=UUID(int=1),
        amount=Decimal("2"),
        created=datetime(2026, 1, 2),
        displayName="Ada",
    )
    assert dump_body(item) == item.model_dump(mode="json", by_alias=True)
