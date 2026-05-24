import functools
import inspect
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from pydantic import BaseModel

from asas.core.models import Payload, Request

F = TypeVar("F", bound=Callable[..., Any])


def _make_request_decorator(method: str) -> Callable:
    def decorator(path: str, response_model: Optional[Any] = None) -> Callable[[F], F]:
        def wrapper(func: F) -> F:
            is_async = inspect.iscoroutinefunction(func)
            sig = inspect.signature(func)

            def _prepare_request(
                self: Any, args: tuple, kwargs: Dict[str, Any]
            ) -> Request:
                # Use bind_partial to avoid TypeError for missing injected arguments (like 'response')
                bound_args = sig.bind_partial(self, *args, **kwargs)
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
                    elif isinstance(value, list) and all(
                        isinstance(i, BaseModel) for i in value
                    ):
                        json_data = [i.model_dump() for i in value]
                    else:
                        # Default to query parameters for other simple types
                        if value is not None:
                            query_params[name] = value

                url = f"{self.base_url}/{actual_path.lstrip('/')}"
                payload = Payload(json=json_data) if json_data is not None else None
                return Request(
                    method=method, url=url, params=query_params, payload=payload
                )

            def _parse_response(response: Any) -> Any:
                if response_model:
                    from pydantic import TypeAdapter

                    adapter = TypeAdapter(response_model)
                    return adapter.validate_python(response.json())
                return response

            @functools.wraps(func)
            async def async_inner(self: Any, *args: Any, **kwargs: Any) -> Any:
                request = _prepare_request(self, args, kwargs)
                response = await self.engine.asend(request)
                parsed = _parse_response(response)
                # If the function is just a placeholder (pass or ...),
                # we return the parsed response directly to improve DX.
                # Otherwise, we call the function with the parsed response.
                result = await func(self, parsed, *args, **kwargs)
                return result if result is not None else parsed

            @functools.wraps(func)
            def sync_inner(self: Any, *args: Any, **kwargs: Any) -> Any:
                request = _prepare_request(self, args, kwargs)
                response = self.engine.send(request)
                parsed = _parse_response(response)
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
