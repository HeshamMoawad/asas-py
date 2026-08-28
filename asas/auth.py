import base64
from enum import Enum
from typing import Any, Callable, List, Optional, Protocol, Union, runtime_checkable

from asas.core.models import Request, Response
from asas.refresh import RefreshCondition, evaluate_refresh, refresh_on_status


class APIKeyLocation(str, Enum):
    """Where an API key is placed in the request."""

    HEADER = "header"
    QUERY = "query"
    COOKIE = "cookie"


@runtime_checkable
class Auth(Protocol):
    """Protocol for authentication strategies."""

    def apply(self, request: Request) -> Request:
        """Apply authentication to the request."""
        ...


@runtime_checkable
class RefreshableAuth(Auth, Protocol):
    """Protocol for authentication strategies that support refreshing.

    By default, on a ``401`` the client calls :meth:`refresh` / :meth:`arefresh`,
    rebuilds the request and retries it exactly once. A strategy can override
    *when* this happens by exposing an optional ``should_refresh(response)``
    method (see :mod:`asas.refresh`); without it, the default ``401`` check is
    used, so existing strategies keep working unchanged.
    """

    def refresh(self) -> None:
        """Refresh authentication synchronously."""
        ...

    async def arefresh(self) -> None:
        """Refresh authentication asynchronously."""
        ...


@runtime_checkable
class ChallengeResponseAuth(Auth, Protocol):
    """Protocol for schemes that answer a server challenge.

    On a ``401`` the client passes the response to :meth:`handle_challenge`. If
    it returns ``True`` the request is rebuilt (re-applying auth, which can now
    use the challenge) and retried exactly once.
    """

    def handle_challenge(self, response: Response) -> bool:
        """Process a ``401`` challenge; return ``True`` to retry the request."""
        ...


class NoAuth(Auth):
    """Explicit "no authentication" strategy.

    Useful as a readable, intentional default in place of ``None``.
    """

    def apply(self, request: Request) -> Request:
        return request


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
        refresh_when: Optional[RefreshCondition] = None,
    ) -> None:
        self.token = token
        self.key = key_name
        self.token_prefix = token_prefix
        self.refresh_callback = refresh_callback
        self.async_refresh_callback = async_refresh_callback
        self.refresh_when: RefreshCondition = refresh_when or refresh_on_status(401)

    def apply(self, request: Request) -> Request:
        request.headers[self.key] = f"{self.token_prefix}{self.token}"
        return request

    def should_refresh(self, response: Response) -> bool:
        return self.refresh_when(response)

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
    Supports passing the key in headers, query parameters, or cookies.
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
        elif self.location == APIKeyLocation.QUERY:
            if request.params is None:
                request.params = {}
            request.params[self.name] = self.key
        else:  # APIKeyLocation.COOKIE
            cookie = f"{self.name}={self.key}"
            existing = request.headers.get("Cookie")
            request.headers["Cookie"] = f"{existing}; {cookie}" if existing else cookie
        return request


class CompositeAuth(RefreshableAuth):
    """Apply several authentication strategies to one request, in order.

    Handy when an API needs more than one credential at once (e.g. an API key
    *and* a bearer token). Refresh and challenge handling are delegated to any
    member strategies that support them.
    """

    def __init__(self, *strategies: Auth) -> None:
        self.strategies: List[Auth] = list(strategies)

    def apply(self, request: Request) -> Request:
        for strategy in self.strategies:
            request = strategy.apply(request)
        return request

    def should_refresh(self, response: Response) -> bool:
        return any(
            evaluate_refresh(strategy, response)
            for strategy in self.strategies
            if isinstance(strategy, RefreshableAuth)
        )

    def refresh(self) -> None:
        for strategy in self.strategies:
            if isinstance(strategy, RefreshableAuth):
                strategy.refresh()

    async def arefresh(self) -> None:
        for strategy in self.strategies:
            if isinstance(strategy, RefreshableAuth):
                await strategy.arefresh()

    def handle_challenge(self, response: Response) -> bool:
        handled = False
        for strategy in self.strategies:
            if isinstance(strategy, ChallengeResponseAuth):
                handled = strategy.handle_challenge(response) or handled
        return handled
