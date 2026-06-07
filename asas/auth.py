import base64
from enum import Enum
from typing import Any, Callable, Optional, Protocol, Union, runtime_checkable

from asas.core.models import Request


class APIKeyLocation(str, Enum):
    """Where an API key is placed in the request."""

    HEADER = "header"
    QUERY = "query"


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


class BasicAuth(Auth):
    """HTTP Basic Authentication."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def apply(self, request: Request) -> Request:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode("ascii")).decode("ascii")
        request.headers["Authorization"] = f"Basic {encoded}"
        return request


class BearerAuth(Auth):
    """Bearer Token Authentication."""

    def __init__(self, token: str) -> None:
        self.token = token

    def apply(self, request: Request) -> Request:
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class RefreshingBearerAuth(RefreshableAuth):
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


class APIKeyAuth(Auth):
    """
    API Key Authentication.
    Supports passing the key in headers or query parameters.
    """

    def __init__(
        self,
        key: str,
        name: str = "X-API-Key",
        location: Union[APIKeyLocation, str] = APIKeyLocation.HEADER,
    ) -> None:
        self.key = key
        self.name = name
        if isinstance(location, APIKeyLocation):
            self.location = location
        else:
            try:
                self.location = APIKeyLocation(location.lower())
            except ValueError:
                raise ValueError(
                    "location must be one of "
                    f"{[loc.value for loc in APIKeyLocation]}"
                ) from None

    def apply(self, request: Request) -> Request:
        if self.location == APIKeyLocation.HEADER:
            request.headers[self.name] = self.key
        else:
            if request.params is None:
                request.params = {}
            request.params[self.name] = self.key
        return request
