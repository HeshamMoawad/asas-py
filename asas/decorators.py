import functools
import inspect
from typing import Any, Callable, Dict, Optional, TypeVar

from pydantic import BaseModel

from asas.core.models import Payload, Request
from asas.refresh import evaluate_refresh

F = TypeVar("F", bound=Callable[..., Any])


def _build_request(
    method: str,
    path: str,
    sig: inspect.Signature,
    base_url: str,
    instance: Any,
    args: tuple,
    kwargs: Dict[str, Any],
    use_auth: bool = True,
) -> Request:
    """Extracts parameters from function call and builds a Request object."""
    bound_args = sig.bind_partial(instance, *args, **kwargs)
    bound_args.apply_defaults()

    actual_path = path
    query_params: Dict[str, Any] = {}
    json_data: Optional[Any] = None

    for name, value in bound_args.arguments.items():
        if name == "self":
            continue

        placeholder = f"{{{name}}}"
        if placeholder in actual_path:
            actual_path = actual_path.replace(placeholder, str(value))
        elif isinstance(value, BaseModel):
            json_data = value.model_dump()
        elif isinstance(value, list) and all(isinstance(i, BaseModel) for i in value):
            json_data = [i.model_dump() for i in value]
        else:
            if value is not None:
                query_params[name] = value

    url = f"{base_url}/{actual_path.lstrip('/')}"
    payload = Payload(json=json_data) if json_data is not None else None
    request = Request(method=method, url=url, params=query_params, payload=payload)

    if use_auth and hasattr(instance, "auth") and instance.auth:
        request = instance.auth.apply(request)

    return request


def _parse_response(response: Any, response_model: Optional[Any] = None) -> Any:
    """Parses the response using Pydantic if a response_model is provided."""
    if response_model:
        from pydantic import TypeAdapter

        adapter = TypeAdapter(response_model)
        return adapter.validate_python(response.json())
    return response


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


def execute_sync(
    instance: Any, build: Callable[[], Request], use_auth: bool = True
) -> Any:
    """Send a request synchronously, retrying once on a ``401``.

    ``build`` returns a fresh :class:`Request` each call so the retry re-applies
    any refreshed credentials. Shared by the request decorators and resources so
    the auth-retry behaviour stays identical everywhere.
    """
    from asas.auth import ChallengeResponseAuth, RefreshableAuth

    _ensure_engine_capability(instance.engine, "send")
    response = instance.engine.send(build())

    if use_auth:
        auth = getattr(instance, "auth", None)
        retry = False
        if response.status_code == 401 and isinstance(auth, ChallengeResponseAuth):
            retry = auth.handle_challenge(response)
        if (
            not retry
            and isinstance(auth, RefreshableAuth)
            and evaluate_refresh(auth, response)
        ):
            auth.refresh()
            retry = True
        if retry:
            response = instance.engine.send(build())
    return response


async def execute_async(
    instance: Any, build: Callable[[], Request], use_auth: bool = True
) -> Any:
    """Asynchronous counterpart of :func:`execute_sync`."""
    from asas.auth import ChallengeResponseAuth, RefreshableAuth

    _ensure_engine_capability(instance.engine, "asend")
    response = await instance.engine.asend(build())

    if use_auth:
        auth = getattr(instance, "auth", None)
        retry = False
        if response.status_code == 401 and isinstance(auth, ChallengeResponseAuth):
            retry = auth.handle_challenge(response)
        if (
            not retry
            and isinstance(auth, RefreshableAuth)
            and evaluate_refresh(auth, response)
        ):
            await auth.arefresh()
            retry = True
        if retry:
            response = await instance.engine.asend(build())
    return response


def _make_request_decorator(method: str) -> Callable:
    def decorator(
        path: str, response_model: Optional[Any] = None, use_auth: bool = True
    ) -> Callable[[F], F]:
        def wrapper(func: F) -> F:
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)

            @functools.wraps(func)
            async def async_inner(self: Any, *args: Any, **kwargs: Any) -> Any:
                def build() -> Request:
                    return _build_request(
                        method, path, sig, self.base_url, self, args, kwargs, use_auth
                    )

                response = await execute_async(self, build, use_auth)
                parsed = _parse_response(response, response_model)
                result = await func(self, parsed, *args, **kwargs)
                return result if result is not None else parsed

            @functools.wraps(func)
            def sync_inner(self: Any, *args: Any, **kwargs: Any) -> Any:
                def build() -> Request:
                    return _build_request(
                        method, path, sig, self.base_url, self, args, kwargs, use_auth
                    )

                response = execute_sync(self, build, use_auth)
                parsed = _parse_response(response, response_model)
                result = func(self, parsed, *args, **kwargs)
                return result if result is not None else parsed

            return async_inner if is_async else sync_inner  # type: ignore[return-value]

        return wrapper

    return decorator


get = _make_request_decorator("GET")
post = _make_request_decorator("POST")
put = _make_request_decorator("PUT")
delete = _make_request_decorator("DELETE")
patch = _make_request_decorator("PATCH")
