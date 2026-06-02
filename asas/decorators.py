import functools
import inspect
from typing import Any, Callable, Dict, Optional, TypeVar

from pydantic import BaseModel

from asas.core.models import Payload, Request

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
        raise TypeError(
            f"Engine {type(engine).__name__} does not support {mode} requests. "
            f"Make sure your engine implements {protocol} protocol."
        )


def _make_request_decorator(method: str) -> Callable:
    def decorator(
        path: str, response_model: Optional[Any] = None, use_auth: bool = True
    ) -> Callable[[F], F]:
        from asas.auth import RefreshableAuth

        def wrapper(func: F) -> F:
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)

            @functools.wraps(func)
            async def async_inner(self: Any, *args: Any, **kwargs: Any) -> Any:
                request = _build_request(
                    method, path, sig, self.base_url, self, args, kwargs, use_auth
                )
                _ensure_engine_capability(self.engine, "asend")
                response = await self.engine.asend(request)

                if (
                    use_auth
                    and response.status_code == 401
                    and isinstance(self.auth, RefreshableAuth)
                ):
                    await self.auth.arefresh()
                    # Re-build request to apply new auth
                    request = _build_request(
                        method, path, sig, self.base_url, self, args, kwargs, use_auth
                    )
                    response = await self.engine.asend(request)

                parsed = _parse_response(response, response_model)
                result = await func(self, parsed, *args, **kwargs)
                return result if result is not None else parsed

            @functools.wraps(func)
            def sync_inner(self: Any, *args: Any, **kwargs: Any) -> Any:
                request = _build_request(
                    method, path, sig, self.base_url, self, args, kwargs, use_auth
                )
                _ensure_engine_capability(self.engine, "send")
                response = self.engine.send(request)

                if (
                    use_auth
                    and response.status_code == 401
                    and isinstance(self.auth, RefreshableAuth)
                ):
                    self.auth.refresh()
                    # Re-build request to apply new auth
                    request = _build_request(
                        method, path, sig, self.base_url, self, args, kwargs, use_auth
                    )
                    response = self.engine.send(request)

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
