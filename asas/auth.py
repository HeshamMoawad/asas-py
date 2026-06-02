import base64
from typing import Any, Callable, Optional, Protocol, runtime_checkable

from asas.core.models import Request


@runtime_checkable
class Auth(Protocol):
    """Protocol for authentication strategies."""

    def apply(self, request: Request) -> Request:
        """Apply authentication to the request."""
        ...


@runtime_checkable
class RefreshableAuth(Auth, Protocol):
    """Protocol for authentication strategies that support refreshing."""

    def refresh(self) -> None:
        """Refresh authentication synchronously."""
        ...

    async def arefresh(self) -> None:
        """Refresh authentication asynchronously."""
        ...


class BasicAuth:
    """HTTP Basic Authentication."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def apply(self, request: Request) -> Request:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode("ascii")).decode("ascii")
        request.headers["Authorization"] = f"Basic {encoded}"
        return request


class BearerAuth:
    """Bearer Token Authentication."""

    def __init__(self, token: str) -> None:
        self.token = token

    def apply(self, request: Request) -> Request:
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class RefreshingBearerAuth:
    """
    Bearer Token Authentication with automatic refresh support.
    """

    def __init__(
        self,
        token: str,
        key_name: str = "Authorization",
        token_prefix: str = "Bearer ",
        refresh_callback: Optional[Callable[[], str]] = None,
        async_refresh_callback: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.token = token
        self.key = key_name
        self.token_prefix = token_prefix
        self.refresh_callback = refresh_callback
        self.async_refresh_callback = async_refresh_callback

    def apply(self, request: Request) -> Request:
        request.headers[self.key] = f"{self.token_prefix}{self.token}"
        return request

    def refresh(self) -> None:
        if self.refresh_callback:
            self.token = self.refresh_callback()
        else:
            raise NotImplementedError("Sync refresh callback not provided")

    async def arefresh(self) -> None:
        if self.async_refresh_callback:
            self.token = await self.async_refresh_callback()
        elif self.refresh_callback:
            self.token = self.refresh_callback()
        else:
            raise NotImplementedError("No refresh callback provided")


class APIKeyAuth:
    """
    API Key Authentication.
    Supports passing the key in headers or query parameters.
    """

    def __init__(
        self, key: str, name: str = "X-API-Key", location: str = "header"
    ) -> None:
        self.key = key
        self.name = name
        self.location = location.lower()

        if self.location not in ("header", "query"):
            raise ValueError("location must be either 'header' or 'query'")

    def apply(self, request: Request) -> Request:
        if self.location == "header":
            request.headers[self.name] = self.key
        else:
            if request.params is None:
                request.params = {}
            request.params[self.name] = self.key
        return request
