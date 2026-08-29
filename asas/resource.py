"""Resources: grouped, convention-driven endpoints with lazy pagination.

A resource is attached to a client as a class attribute and bound to that client
on access (sharing its ``base_url`` / ``engine`` / ``auth``). Declaring a
``path`` (and optional ``model``) gives ``list`` / ``get`` / ``create`` /
``update`` / ``delete`` plus lazy iteration for free, and you can still add
custom ``@get`` / ``@post`` endpoints to the same class.

```python
class Users(AsasResource):
    path = "/users"
    model = User

class MyClient(AsasClient):
    users = Users()

client.users.create(User(...))
for user in client.users:        # lazy auto-pagination, no loop code
    print(user.name)
```
"""

import copy
from typing import Any, AsyncIterator, Dict, Iterator, Optional, Type, TypeVar

from pydantic import BaseModel

from asas.core.models import Payload, Request, Response
from asas.decorators import execute_async, execute_sync
from asas.pagination import PageNumberPaginator, PageRequest, Paginator

T = TypeVar("T", bound="BaseResource")


def _join(base: str, *parts: Any) -> str:
    """Join a base URL with path parts, normalising the slashes between them."""
    url = base.rstrip("/")
    for part in parts:
        url = f"{url}/{str(part).strip('/')}"
    return url


def _payload(body: Any) -> Optional[Payload]:
    """Build a JSON :class:`Payload` from a model, list of models, or dict."""
    if body is None:
        return None
    json_data: Any
    if isinstance(body, BaseModel):
        json_data = body.model_dump()
    elif isinstance(body, list) and all(isinstance(i, BaseModel) for i in body):
        json_data = [i.model_dump() for i in body]
    else:
        json_data = body
    return Payload(json=json_data)


class BaseResource:
    """Shared binding, configuration, and request building for resources."""

    #: Base path of the resource, e.g. ``"/users"``. Required for CRUD/iteration.
    path: str = ""
    #: Pydantic model used to validate records. ``None`` yields raw JSON.
    model: Optional[Type[Any]] = None
    #: Pagination strategy for iteration. Defaults to page-number pagination.
    paginator: Optional[Paginator] = None

    def __init__(
        self,
        path: Optional[str] = None,
        model: Optional[Type[Any]] = None,
        paginator: Optional[Paginator] = None,
    ) -> None:
        if path is not None:
            self.path = path
        if model is not None:
            self.model = model
        if paginator is not None:
            self.paginator = paginator
        self._client: Any = None
        self._name: Optional[str] = None

    # -- descriptor binding -------------------------------------------------

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def __get__(self: T, instance: Any, owner: Optional[type] = None) -> T:
        if instance is None:
            return self
        cache: Dict[Any, Any] = instance.__dict__.setdefault("__asas_resources__", {})
        key = self._name or id(self)
        if key not in cache:
            cache[key] = self._bind(instance)
        return cache[key]  # type: ignore[no-any-return]

    def _bind(self: T, client: Any) -> T:
        bound = copy.copy(self)
        bound._client = client
        bound.__dict__.pop("_adapter_cache", None)
        return bound

    # -- client passthroughs ------------------------------------------------

    @property
    def base_url(self) -> str:
        return self._client.base_url  # type: ignore[no-any-return]

    @property
    def engine(self) -> Any:
        return self._client.engine

    @property
    def auth(self) -> Any:
        return self._client.auth

    # -- helpers ------------------------------------------------------------

    def _require_path(self) -> None:
        if not self.path:
            raise ValueError(
                f"{type(self).__name__} needs a `path` for CRUD/iteration "
                "(e.g. `path = '/users'`)."
            )

    def _adapter(self) -> Optional[Any]:
        if self.model is None:
            return None
        cached = self.__dict__.get("_adapter_cache")
        if cached is None:
            from pydantic import TypeAdapter

            cached = TypeAdapter(self.model)
            self.__dict__["_adapter_cache"] = cached
        return cached

    def _resolve_paginator(self) -> Paginator:
        return self.paginator or PageNumberPaginator()

    def _parse_one(self, response: Response) -> Any:
        adapter = self._adapter()
        data = response.json()
        return adapter.validate_python(data) if adapter else data

    def _parse_items(self, items: Any) -> Any:
        adapter = self._adapter()
        if adapter is None:
            return items
        return [adapter.validate_python(item) for item in items]

    def _build(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Any = None,
    ) -> Request:
        request = Request(
            method=method,
            url=_join(self.base_url, path),
            params=params or {},
            payload=_payload(body),
        )
        auth = self.auth
        if auth is not None:
            request = auth.apply(request)
        return request

    def _build_page(self, page: PageRequest) -> Request:
        if page.url is not None:
            request = Request(method="GET", url=page.url, params={}, payload=None)
        else:
            self._require_path()
            request = Request(
                method="GET",
                url=_join(self.base_url, self.path),
                params=dict(page.params),
                payload=None,
            )
        auth = self.auth
        if auth is not None:
            request = auth.apply(request)
        return request


class AsasResource(BaseResource):
    """Synchronous resource. Use on subclasses of :class:`~asas.AsasClient`."""

    def list(self, **params: Any) -> Any:
        """Fetch a single page of records (no pagination)."""
        self._require_path()
        response = execute_sync(self, lambda: self._build("GET", self.path, params))
        items = self._resolve_paginator().extract_items(response)
        return self._parse_items(items)

    def get(self, id: Any) -> Any:
        """Fetch one record by id."""
        self._require_path()
        response = execute_sync(self, lambda: self._build("GET", f"{self.path}/{id}"))
        return self._parse_one(response)

    def create(self, obj: Any) -> Any:
        """Create a record from a Pydantic model (or dict)."""
        self._require_path()
        response = execute_sync(self, lambda: self._build("POST", self.path, body=obj))
        return self._parse_one(response)

    def update(self, id: Any, obj: Any) -> Any:
        """Replace a record by id (``PUT``)."""
        self._require_path()
        response = execute_sync(
            self, lambda: self._build("PUT", f"{self.path}/{id}", body=obj)
        )
        return self._parse_one(response)

    def delete(self, id: Any) -> Response:
        """Delete a record by id; returns the raw :class:`Response`."""
        self._require_path()
        return execute_sync(  # type: ignore[no-any-return]
            self, lambda: self._build("DELETE", f"{self.path}/{id}")
        )

    def iterate(self, **params: Any) -> Iterator[Any]:
        """Lazily yield every record across all pages — no loop code required."""
        self._require_path()
        paginator = self._resolve_paginator()
        adapter = self._adapter()
        page: Optional[PageRequest] = paginator.first_page(params)
        while page is not None:
            current = page
            response = execute_sync(self, lambda: self._build_page(current))
            for item in paginator.extract_items(response):
                yield adapter.validate_python(item) if adapter else item
            page = paginator.next_page(response, current)

    def __iter__(self) -> Iterator[Any]:
        return self.iterate()


class AsasAsyncResource(BaseResource):
    """Asynchronous resource. Use on subclasses of :class:`~asas.AsasAsyncClient`."""

    async def list(self, **params: Any) -> Any:
        """Fetch a single page of records (no pagination)."""
        self._require_path()
        response = await execute_async(
            self, lambda: self._build("GET", self.path, params)
        )
        items = self._resolve_paginator().extract_items(response)
        return self._parse_items(items)

    async def get(self, id: Any) -> Any:
        """Fetch one record by id."""
        self._require_path()
        response = await execute_async(
            self, lambda: self._build("GET", f"{self.path}/{id}")
        )
        return self._parse_one(response)

    async def create(self, obj: Any) -> Any:
        """Create a record from a Pydantic model (or dict)."""
        self._require_path()
        response = await execute_async(
            self, lambda: self._build("POST", self.path, body=obj)
        )
        return self._parse_one(response)

    async def update(self, id: Any, obj: Any) -> Any:
        """Replace a record by id (``PUT``)."""
        self._require_path()
        response = await execute_async(
            self, lambda: self._build("PUT", f"{self.path}/{id}", body=obj)
        )
        return self._parse_one(response)

    async def delete(self, id: Any) -> Response:
        """Delete a record by id; returns the raw :class:`Response`."""
        self._require_path()
        return await execute_async(  # type: ignore[no-any-return]
            self, lambda: self._build("DELETE", f"{self.path}/{id}")
        )

    async def iterate(self, **params: Any) -> AsyncIterator[Any]:
        """Lazily yield every record across all pages — no loop code required."""
        self._require_path()
        paginator = self._resolve_paginator()
        adapter = self._adapter()
        page: Optional[PageRequest] = paginator.first_page(params)
        while page is not None:
            current = page
            response = await execute_async(self, lambda: self._build_page(current))
            for item in paginator.extract_items(response):
                yield adapter.validate_python(item) if adapter else item
            page = paginator.next_page(response, current)

    def __aiter__(self) -> AsyncIterator[Any]:
        return self.iterate()
