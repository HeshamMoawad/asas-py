from __future__ import annotations

import inspect
from typing import Annotated, Any, Callable, Optional

import pytest
import respx
from httpx import Response as HttpxResponse
from pydantic import BaseModel

from asas import AsasClient, get
from asas.core.models import Response
from asas.endpoint import EndpointOptions, EndpointSpec
from asas.params import Body, Cookie, File, Form, Header, Location, Path, Query

PATH, QUERY, BODY = Location.PATH, Location.QUERY, Location.BODY


class User(BaseModel):
    id: int


def compile_(
    method: str, path: str, func: Callable[..., Any], **opts: Any
) -> EndpointSpec:
    return EndpointSpec.compile(method, path, func, EndpointOptions(**opts))


def f_model_body(self: Any, id: int, user: User, q: str | None = None) -> User:
    raise NotImplementedError


def f_dict_body(self: Any, filters: dict[str, Any]) -> User:
    raise NotImplementedError


def f_optional_list_body(self: Any, users: list[User] | None = None) -> User:
    raise NotImplementedError


@pytest.mark.parametrize(
    "func,path,expected",
    [
        (f_model_body, "/u/{id}", {"id": PATH, "user": BODY, "q": QUERY}),
        (f_dict_body, "/x", {"filters": BODY}),
        (f_optional_list_body, "/x", {"users": BODY}),
    ],
)
def test_infers_locations(func: Any, path: Any, expected: Any) -> None:
    spec = compile_("POST", path, func)
    assert {p.name: p.location for p in spec.params} == expected


def f_marker(self: Any, q: Annotated[int, Header()]) -> User:
    raise NotImplementedError


def test_marker_overrides_inference() -> None:
    p = compile_("GET", "/x", f_marker).params[0]
    assert p.location is Location.HEADER and p.wire_name == "Q"
    assert p.annotation is int


def f_trace(self: Any, x_trace: Annotated[str, Header()]) -> User:
    raise NotImplementedError


def test_header_default_alias() -> None:
    assert compile_("GET", "/x", f_trace).params[0].wire_name == "X-Trace"


def f_alias(self: Any, user_id: Annotated[int, Path(alias="userId")]) -> User:
    raise NotImplementedError


def test_path_alias_matches_placeholder() -> None:
    spec = compile_("GET", "/users/{userId}", f_alias)
    assert spec.params[0].wire_name == "userId"
    assert spec.params[0].location is Location.PATH


def _with_hints(**hints: Any) -> Callable[..., Any]:
    """An endpoint whose resolved hints are exactly ``hints`` (no interpreter
    rewriting), with every parameter defaulting to ``None``."""

    def f(self: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    params = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    params += [
        inspect.Parameter(n, inspect.Parameter.KEYWORD_ONLY, default=None)
        for n in hints
    ]
    f.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    f.__annotations__ = {**hints, "return": Response}
    return f


def test_marker_found_in_optional_wrapped_annotated() -> None:
    # Python 3.10's get_type_hints wraps ``= None`` params in Optional[...].
    f = _with_hints(x_trace=Optional[Annotated[str | None, Header("X-Trace")]])
    spec = compile_("GET", "/x", f)
    p = spec.params[0]
    assert p.location is Location.HEADER and p.wire_name == "X-Trace"
    assert p.annotation == Optional[str]
    request = spec.build_request("http://h", (), {"x_trace": "t"})
    assert request.headers == {"X-Trace": "t"} and request.params is None


def test_marker_found_in_outside_in_optional() -> None:
    f = _with_hints(
        expand=Optional[Annotated[str, Query(alias="x-expand")]],
        sid=Optional[Annotated[str, Cookie()]],
    )
    spec = compile_("GET", "/x", f)
    expand, sid = spec.params
    assert expand.location is Location.QUERY and expand.wire_name == "x-expand"
    assert sid.location is Location.COOKIE and sid.wire_name == "sid"
    assert expand.annotation == Optional[str] and sid.annotation == Optional[str]
    request = spec.build_request("http://h", (), {"expand": "e", "sid": "s"})
    assert request.params == {"x-expand": "e"} and request.cookies == {"sid": "s"}


def placeholder_without_param(self: Any) -> User:
    raise NotImplementedError


def path_param_without_placeholder(self: Any, id: Annotated[int, Path()]) -> User:
    raise NotImplementedError


def two_bodies(self: Any, a: User, b: User) -> User:
    raise NotImplementedError


def body_with_form(self: Any, a: User, b: Annotated[str, Form()]) -> User:
    raise NotImplementedError


def body_with_file(self: Any, a: User, b: Annotated[bytes, File()]) -> User:
    raise NotImplementedError


def duplicate_wire_name(self: Any, a: int, b: Annotated[int, Query(alias="a")]) -> User:
    raise NotImplementedError


def missing_return_annotation(self: Any, a: int):  # type: ignore[no-untyped-def]
    raise NotImplementedError


def unannotated_param(self: Any, a) -> User:  # type: ignore[no-untyped-def]
    raise NotImplementedError


def marker_displaces_placeholder(self: Any, id: Annotated[int, Query()]) -> User:
    raise NotImplementedError


CASES: dict[str, tuple[Callable[..., Any], str]] = {
    "placeholder_without_param": (placeholder_without_param, "/u/{id}"),
    "path_param_without_placeholder": (path_param_without_placeholder, "/u"),
    "two_bodies": (two_bodies, "/u"),
    "body_with_form": (body_with_form, "/u"),
    "body_with_file": (body_with_file, "/u"),
    "duplicate_wire_name": (duplicate_wire_name, "/u"),
    "missing_return_annotation": (missing_return_annotation, "/u"),
    "unannotated_param": (unannotated_param, "/u"),
    "marker_displaces_placeholder": (marker_displaces_placeholder, "/u/{id}"),
}


@pytest.mark.parametrize("case", list(CASES))
def test_declaration_errors_raise_type_error(case: Any) -> None:
    func, path = CASES[case]
    with pytest.raises(TypeError, match=func.__name__):
        compile_("POST", path, func)


def test_same_wire_name_in_different_locations_is_allowed() -> None:
    def f(self: Any, a: int, b: Annotated[int, Header("a")]) -> User:
        raise NotImplementedError

    assert len(compile_("GET", "/x", f).params) == 2


@pytest.mark.parametrize(
    "ann,kind,optional",
    [
        (Response, "response", False),
        (None, "none", False),
        (bytes, "bytes", False),
        (str, "str", False),
        (User, "model", False),
        (list[User], "model", False),
        (Optional[User], "model", True),
        (dict[str, Any], "model", False),
    ],
)
def test_return_kinds(ann: Any, kind: Any, optional: Any) -> None:
    def f(self: Any) -> Any:
        raise NotImplementedError

    f.__annotations__["return"] = ann
    spec = compile_("GET", "/x", f)
    assert spec.return_kind == kind
    assert spec.returns_optional is optional
    assert (spec.return_adapter is not None) is (kind == "model")


def test_effective_raise_for_status() -> None:
    def r(self: Any) -> Response:
        raise NotImplementedError

    def u(self: Any) -> User:
        raise NotImplementedError

    assert (
        compile_("GET", "/x", r, raise_for_status=True).effective_raise_for_status
        is False
    )
    assert compile_("GET", "/x", u).effective_raise_for_status is None
    assert (
        compile_("GET", "/x", u, raise_for_status=True).effective_raise_for_status
        is True
    )


def test_detects_async() -> None:
    async def a(self: Any) -> User:
        raise NotImplementedError

    def s(self: Any) -> User:
        raise NotImplementedError

    assert compile_("GET", "/x", a).is_async is True
    assert compile_("GET", "/x", s).is_async is False


def f_forward(self: Any) -> "LaterModel":  # type: ignore[name-defined]  # noqa: F821
    raise NotImplementedError


def test_forward_reference_raises_name_error_until_defined() -> None:
    with pytest.raises(NameError):
        compile_("GET", "/x", f_forward)
    globals()["LaterModel"] = User
    try:
        assert compile_("GET", "/x", f_forward).return_kind == "model"
    finally:
        del globals()["LaterModel"]


def f_var_args(self: Any, *args: int) -> User:
    raise NotImplementedError


def f_var_kwargs(self: Any, **kwargs: int) -> User:
    raise NotImplementedError


@pytest.mark.parametrize("func", [f_var_args, f_var_kwargs])
def test_var_positional_and_keyword_rejected(func: Callable[..., Any]) -> None:
    with pytest.raises(TypeError, match=func.__qualname__):
        compile_("GET", "/x", func)


# --- Decorator integration ---------------------------------------------------

BASE = "https://api.example.com"


def test_decorator_raises_type_error_at_class_definition() -> None:
    with pytest.raises(TypeError, match="placeholder"):

        class Bad(AsasClient):
            @get("/x/{id}")
            def broken(self) -> Response:
                raise NotImplementedError


class ForwardClient(AsasClient):
    @get("/later")
    def later(self) -> LaterResult:
        raise NotImplementedError


class LaterResult(BaseModel):
    value: int


def test_forward_reference_resolved_on_first_call() -> None:
    client = ForwardClient(BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/later").mock(return_value=HttpxResponse(200, json={"value": 3}))
        assert client.later() == LaterResult(value=3)
        assert client.later() == LaterResult(value=3)


def test_body_never_executes() -> None:
    calls: list[int] = []

    class Counting(AsasClient):
        @get("/x")
        def x(self) -> Response:
            calls.append(1)
            raise AssertionError("body must not run")

    with respx.mock(base_url=BASE) as mock:
        mock.get("/x").mock(return_value=HttpxResponse(200))
        assert Counting(BASE).x().status_code == 200
    assert calls == []
