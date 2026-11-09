"""Request decorators and the shared send pipeline.

Every request, whether from a decorated endpoint or a resource method, goes
through :func:`execute_sync` / :func:`execute_async`::

    build → auth.apply (if use_auth) → on_request* → engine.send → on_response*
        → on a 401 challenge / refresh: rebuild and resend exactly once
        → status check (HTTPStatusError) → parse (ResponseValidationError)

``TransportError``, ``HTTPStatusError`` and ``ResponseValidationError`` raised by
the pipeline are passed to the ``on_error`` hooks, then re-raised unchanged.
"""

import functools
import inspect
from typing import Any, Callable, Mapping, Optional, Protocol, Tuple, TypeVar, cast

from asas.auth import ChallengeResponseAuth, RefreshableAuth
from asas.core.models import Request, Response
from asas.endpoint import EndpointOptions, EndpointSpec
from asas.errors import (
    HTTPStatusError,
    ResponseValidationError,
    TransportError,
    error_for_response,
)
from asas.hooks import Hooks
from asas.refresh import evaluate_refresh

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def _ensure_engine_capability(engine: Any, method_name: str) -> None:
    """Checks if the engine supports the requested communication mode."""
    if not hasattr(engine, method_name):
        mode = "asynchronous" if method_name == "asend" else "synchronous"
        protocol = "AsyncEngine" if method_name == "asend" else "SyncEngine"
        hint = ""
        if method_name == "asend" and type(engine).__name__ == "RequestsSyncEngine":
            hint = (
                " The `requests` engine is synchronous only (it has no async "
                "support). Use `AsasClient` instead of `AsasAsyncClient`, or "
                "pass an httpx engine (e.g. `HTTPXAsyncEngine`)."
            )
        raise TypeError(
            f"Engine {type(engine).__name__} does not support {mode} requests. "
            f"Make sure your engine implements {protocol} protocol.{hint}"
        )


# -- pipeline steps shared by the sync and async paths ------------------------


def _prepare(
    owner: Any, build: Callable[[], Request], hooks: Hooks, use_auth: bool
) -> Request:
    request = build()
    if use_auth and owner.auth is not None:
        request = owner.auth.apply(request)
    return hooks.apply_request(request)


def _challenge_handled(auth: Any, response: Response) -> bool:
    return (
        response.status_code == 401
        and isinstance(auth, ChallengeResponseAuth)
        and auth.handle_challenge(response)
    )


def _should_refresh(auth: Any, response: Response) -> bool:
    return isinstance(auth, RefreshableAuth) and evaluate_refresh(auth, response)


def _finish(
    request: Request,
    response: Response,
    parse: Callable[[Response], T],
    raise_for_status: bool,
    hooks: Hooks,
) -> T:
    try:
        if raise_for_status and not 200 <= response.status_code < 300:
            raise error_for_response(request, response)
        return parse(response)
    except (HTTPStatusError, ResponseValidationError) as exc:
        hooks.notify_error(exc)
        raise


def _resolve(
    owner: Any, raise_for_status: Optional[bool], hooks: Optional[Hooks]
) -> Tuple[bool, Hooks]:
    effective_raise = (
        owner.raise_for_status if raise_for_status is None else raise_for_status
    )
    return effective_raise, owner.hooks.merged(hooks)


def execute_sync(
    owner: Any,
    build: Callable[[], Request],
    parse: Callable[[Response], T],
    *,
    use_auth: bool = True,
    raise_for_status: Optional[bool] = None,
    hooks: Optional[Hooks] = None,
) -> T:
    """Run the request pipeline synchronously.

    ``owner`` provides ``engine``, ``auth``, ``hooks`` and ``raise_for_status``.
    ``build`` returns a fresh, unauthenticated :class:`Request` on each call so a
    retry picks up refreshed credentials.
    """
    _ensure_engine_capability(owner.engine, "send")
    effective_raise, effective_hooks = _resolve(owner, raise_for_status, hooks)

    def send() -> Tuple[Request, Response]:
        request = _prepare(owner, build, effective_hooks, use_auth)
        try:
            response = owner.engine.send(request)
        except TransportError as exc:
            effective_hooks.notify_error(exc)
            raise
        effective_hooks.notify_response(request, response)
        return request, response

    request, response = send()
    if use_auth:
        auth = owner.auth
        retry = _challenge_handled(auth, response)
        if not retry and _should_refresh(auth, response):
            auth.refresh()
            retry = True
        if retry:
            request, response = send()
    return _finish(request, response, parse, effective_raise, effective_hooks)


async def execute_async(
    owner: Any,
    build: Callable[[], Request],
    parse: Callable[[Response], T],
    *,
    use_auth: bool = True,
    raise_for_status: Optional[bool] = None,
    hooks: Optional[Hooks] = None,
) -> T:
    """Asynchronous counterpart of :func:`execute_sync`."""
    _ensure_engine_capability(owner.engine, "asend")
    effective_raise, effective_hooks = _resolve(owner, raise_for_status, hooks)

    async def send() -> Tuple[Request, Response]:
        request = _prepare(owner, build, effective_hooks, use_auth)
        try:
            response = await owner.engine.asend(request)
        except TransportError as exc:
            effective_hooks.notify_error(exc)
            raise
        effective_hooks.notify_response(request, response)
        return request, response

    request, response = await send()
    if use_auth:
        auth = owner.auth
        retry = _challenge_handled(auth, response)
        if not retry and _should_refresh(auth, response):
            await auth.arefresh()
            retry = True
        if retry:
            request, response = await send()
    return _finish(request, response, parse, effective_raise, effective_hooks)


# -- decorators -----------------------------------------------------------------


class _RequestDecorator(Protocol):
    def __call__(
        self,
        path: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        use_auth: bool = True,
        raise_for_status: Optional[bool] = None,
        hooks: Optional[Hooks] = None,
    ) -> Callable[[F], F]:
        ...


def _make_request_decorator(method: str) -> _RequestDecorator:
    def decorator(
        path: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        use_auth: bool = True,
        raise_for_status: Optional[bool] = None,
        hooks: Optional[Hooks] = None,
    ) -> Callable[[F], F]:
        options = EndpointOptions(
            headers=headers,
            timeout=timeout,
            use_auth=use_auth,
            raise_for_status=raise_for_status,
            hooks=hooks,
        )

        def wrap(func: F) -> F:
            compiled: Optional[EndpointSpec]
            try:
                compiled = EndpointSpec.compile(method, path, func, options)
            except NameError:
                compiled = None  # forward reference: compile on first call

            def spec() -> EndpointSpec:
                nonlocal compiled
                if compiled is None:
                    compiled = EndpointSpec.compile(method, path, func, options)
                return compiled

            def call(
                self: Any, args: Tuple[Any, ...], kwargs: dict[str, Any]
            ) -> Tuple[Callable[[], Request], EndpointSpec]:
                s = spec()
                return (lambda: s.build_request(self.base_url, args, kwargs)), s

            if inspect.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_endpoint(self: Any, *args: Any, **kwargs: Any) -> Any:
                    build, s = call(self, args, kwargs)
                    return await execute_async(
                        self,
                        build,
                        s.parse_response,
                        use_auth=s.options.use_auth,
                        raise_for_status=s.effective_raise_for_status,
                        hooks=s.options.hooks,
                    )

                return cast(F, async_endpoint)

            @functools.wraps(func)
            def sync_endpoint(self: Any, *args: Any, **kwargs: Any) -> Any:
                build, s = call(self, args, kwargs)
                return execute_sync(
                    self,
                    build,
                    s.parse_response,
                    use_auth=s.options.use_auth,
                    raise_for_status=s.effective_raise_for_status,
                    hooks=s.options.hooks,
                )

            return cast(F, sync_endpoint)

        return wrap

    return decorator


get = _make_request_decorator("GET")
post = _make_request_decorator("POST")
put = _make_request_decorator("PUT")
delete = _make_request_decorator("DELETE")
patch = _make_request_decorator("PATCH")
