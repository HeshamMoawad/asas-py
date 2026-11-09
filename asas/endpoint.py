"""Compile a decorated method declaration into an immutable ``EndpointSpec``."""

import inspect
import re
import types
from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    Callable,
    Literal,
    Mapping,
    Optional,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)
from urllib.parse import quote

from pydantic import BaseModel, TypeAdapter, ValidationError

from asas.core.models import Payload, Request, Response
from asas.errors import ResponseValidationError
from asas.hooks import Hooks
from asas.params import Body, Header, Location, Param, Path, Query

ReturnKind = Literal["response", "none", "bytes", "str", "model"]

_NONE_TYPE = type(None)
_PLACEHOLDER = re.compile(r"{([^{}]+)}")


@dataclass(frozen=True)
class EndpointOptions:
    headers: Optional[Mapping[str, str]] = None
    timeout: Optional[float] = None
    use_auth: bool = True
    raise_for_status: Optional[bool] = None
    hooks: Optional[Hooks] = None


@dataclass(frozen=True)
class ParamSpec:
    name: str
    location: Location
    wire_name: str
    annotation: Any
    marker: Param
    adapter: TypeAdapter[Any]


def _is_union(tp: Any) -> bool:
    return get_origin(tp) in (Union, types.UnionType)


def _strip_none(tp: Any) -> Any:
    """Return ``tp`` without ``None`` members of a union."""
    if not _is_union(tp):
        return tp
    members = tuple(a for a in get_args(tp) if a is not _NONE_TYPE)
    if len(members) == 1:
        return members[0]
    return Union[members]  # type: ignore[return-value]


def _is_model(tp: Any) -> bool:
    return inspect.isclass(tp) and issubclass(tp, BaseModel)


def _is_body_type(tp: Any) -> bool:
    tp = _strip_none(tp)
    if _is_model(tp) or tp is dict:
        return True
    origin = get_origin(tp)
    if origin is dict:
        return True
    if origin is list:
        args = get_args(tp)
        return bool(args) and _is_model(args[0])
    return False


def _split_annotated(hint: Any) -> tuple[Any, Optional[Param]]:
    """Return ``(base type, marker)`` for a parameter hint.

    The marker is found in a top-level ``Annotated[T, M]``, or in a union of
    ``None`` and exactly one ``Annotated[T, M]`` member, which is unwrapped to
    ``T | None``. That second form covers ``Annotated[T, M] | None`` and Python
    3.10's ``get_type_hints``, which wraps parameters defaulting to ``None`` in
    ``Optional[...]``.
    """
    if get_origin(hint) is Annotated:
        base, *meta = get_args(hint)
        marker = next((m for m in meta if isinstance(m, Param)), None)
        return base, marker
    if _is_union(hint):
        members = [a for a in get_args(hint) if a is not _NONE_TYPE]
        if len(members) == 1 and get_origin(members[0]) is Annotated:
            base, marker = _split_annotated(members[0])
            if marker is not None:
                return Optional[base], marker
    return hint, None


def _return_kind(ann: Any) -> tuple[ReturnKind, Optional[TypeAdapter[Any]], bool]:
    if ann is None or ann is _NONE_TYPE:
        return "none", None, False
    if ann is Response:
        return "response", None, False
    if ann is bytes:
        return "bytes", None, False
    if ann is str:
        return "str", None, False
    optional = _is_union(ann) and _NONE_TYPE in get_args(ann)
    return "model", TypeAdapter(ann), optional


def dump_body(
    value: Any,
    adapter: Optional[TypeAdapter[Any]] = None,
    *,
    exclude_unset: bool = False,
    exclude_none: bool = False,
) -> Any:
    """Dump ``value`` to JSON-safe data using aliases."""
    if adapter is None:
        adapter = TypeAdapter(type(value))
    return adapter.dump_python(
        value,
        mode="json",
        by_alias=True,
        exclude_unset=exclude_unset,
        exclude_none=exclude_none,
    )


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _wire_value(spec: "ParamSpec", value: Any) -> Any:
    """Dump a non-body value to a string, or a list of strings."""
    dumped = spec.adapter.dump_python(value, mode="json", by_alias=True)
    if isinstance(dumped, (list, tuple)):
        return [_scalar(v) for v in dumped]
    return _scalar(dumped)


class EndpointSpec:
    def __init__(
        self,
        method: str,
        path: str,
        is_async: bool,
        signature: inspect.Signature,
        params: tuple[ParamSpec, ...],
        return_kind: ReturnKind,
        return_adapter: Optional[TypeAdapter[Any]],
        returns_optional: bool,
        options: EndpointOptions,
    ) -> None:
        self.method = method
        self.path = path
        self.is_async = is_async
        self.signature = signature
        self.params = params
        self.return_kind = return_kind
        self.return_adapter = return_adapter
        self.returns_optional = returns_optional
        self.options = options

    @property
    def effective_raise_for_status(self) -> Optional[bool]:
        if self.return_kind == "response":
            return False
        return self.options.raise_for_status

    @classmethod
    def compile(
        cls,
        method: str,
        path: str,
        func: Callable[..., Any],
        options: EndpointOptions,
    ) -> "EndpointSpec":
        name = func.__qualname__
        # NameError from unresolved forward references propagates on purpose.
        hints = get_type_hints(func, include_extras=True)
        signature = inspect.signature(func)
        placeholders = _PLACEHOLDER.findall(path)

        if "return" not in hints:
            raise TypeError(
                f"{name}: missing return annotation "
                "(use '-> Response' to receive the raw response)"
            )

        specs: list[ParamSpec] = []
        for pname in list(signature.parameters)[1:]:  # skip self
            pkind = signature.parameters[pname].kind
            if pkind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                raise TypeError(
                    f"{name}: variadic parameter '{pname}' is not supported"
                )
            if pname not in hints:
                raise TypeError(f"{name}: parameter '{pname}' lacks a type annotation")
            base, marker = _split_annotated(hints[pname])
            if marker is None:
                if pname in placeholders:
                    marker = Path()
                elif _is_body_type(base):
                    marker = Body()
                else:
                    marker = Query()
            if marker.alias:
                wire = marker.alias
            elif isinstance(marker, Header):
                wire = "-".join(p.capitalize() for p in pname.split("_"))
            else:
                wire = pname
            adapter = TypeAdapter(Any if marker.location is Location.FILE else base)
            specs.append(ParamSpec(pname, marker.location, wire, base, marker, adapter))

        cls._validate(name, placeholders, specs)

        kind, return_adapter, optional = _return_kind(hints["return"])
        return cls(
            method=method,
            path=path,
            is_async=inspect.iscoroutinefunction(func),
            signature=signature,
            params=tuple(specs),
            return_kind=kind,
            return_adapter=return_adapter,
            returns_optional=optional,
            options=options,
        )

    def build_request(
        self, base_url: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> Request:
        """Build a ``Request`` (without auth). ``args`` excludes ``self``."""
        bound = self.signature.bind(None, *args, **kwargs)
        bound.apply_defaults()
        values = bound.arguments

        url_path = self.path
        query: dict[str, Any] = {}
        headers: dict[str, str] = dict(self.options.headers or {})
        cookies: dict[str, str] = {}
        form: dict[str, Any] = {}
        files: dict[str, Any] = {}
        payload: Optional[Payload] = None

        for p in self.params:
            value = values[p.name]
            loc = p.location
            if loc is Location.BODY:
                if value is not None:
                    assert isinstance(p.marker, Body)
                    payload = Payload(
                        json=dump_body(
                            value,
                            p.adapter,
                            exclude_unset=p.marker.exclude_unset,
                            exclude_none=p.marker.exclude_none,
                        )
                    )
                continue
            if value is None:
                if loc is Location.PATH:
                    raise ValueError(f"path parameter '{p.name}' must not be None")
                continue
            if loc is Location.FILE:
                files[p.wire_name] = value
                continue
            wire = _wire_value(p, value)
            if loc is Location.PATH:
                url_path = url_path.replace(
                    "{" + p.wire_name + "}", quote(str(wire), safe="")
                )
            elif loc is Location.QUERY:
                query[p.wire_name] = wire
            elif loc is Location.HEADER:
                headers[p.wire_name] = wire
            elif loc is Location.COOKIE:
                cookies[p.wire_name] = wire
            elif loc is Location.FORM:
                form[p.wire_name] = wire

        if files:
            payload = Payload(data=form, files=files)
        elif form:
            payload = Payload(data=form)

        return Request(
            method=self.method,
            url=f"{base_url}/{url_path.lstrip('/')}",
            params=query or None,
            headers=headers,
            cookies=cookies,
            payload=payload,
            timeout=self.options.timeout,
        )

    def parse_response(self, response: Response) -> Any:
        """Convert ``response`` per the return annotation (no status check)."""
        kind = self.return_kind
        if kind == "response":
            return response
        if kind == "none":
            return None
        if kind == "bytes":
            return response.content
        if kind == "str":
            return response.text
        assert self.return_adapter is not None
        if not response.content.strip() and self.returns_optional:
            return None
        try:
            return self.return_adapter.validate_json(response.content)
        except ValidationError as exc:
            raise ResponseValidationError(response, exc) from exc

    @staticmethod
    def _validate(name: str, placeholders: list[str], specs: list[ParamSpec]) -> None:
        path_wires = {s.wire_name for s in specs if s.location is Location.PATH}
        for ph in placeholders:
            if ph not in path_wires:
                raise TypeError(
                    f"{name}: path placeholder '{{{ph}}}' has no matching parameter"
                )
        for s in specs:
            if s.location is Location.PATH and s.wire_name not in placeholders:
                raise TypeError(
                    f"{name}: Path parameter '{s.name}' has no matching "
                    f"placeholder '{{{s.wire_name}}}' in the path"
                )
        locations = [s.location for s in specs]
        if locations.count(Location.BODY) > 1:
            raise TypeError(f"{name}: at most one Body parameter is allowed")
        if Location.BODY in locations and (
            Location.FORM in locations or Location.FILE in locations
        ):
            raise TypeError(f"{name}: Body cannot be combined with Form or File")
        seen: set[tuple[Location, str]] = set()
        for s in specs:
            key = (s.location, s.wire_name)
            if key in seen:
                raise TypeError(
                    f"{name}: duplicate {s.location.value} name '{s.wire_name}'"
                )
            seen.add(key)
