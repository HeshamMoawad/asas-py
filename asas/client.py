from typing import Any, Generic, Optional, TypeVar

from typing_extensions import Self

from asas.auth import Auth
from asas.core.engine import AsyncEngine, SyncEngine
from asas.engines.httpx import HTTPXAsyncEngine, HTTPXSyncEngine
from asas.hooks import Hooks

E = TypeVar("E", SyncEngine, AsyncEngine)


class BaseAsasClient(Generic[E]):
    """
    Base client for building API clients.
    """

    def __init__(
        self,
        base_url: str,
        engine: E,
        *,
        auth: Optional[Auth] = None,
        hooks: Optional[Hooks] = None,
        raise_for_status: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.engine: E = engine
        self._auth = auth
        self.hooks: Hooks = hooks if hooks is not None else Hooks()
        self.raise_for_status = raise_for_status

    @property
    def auth(self) -> Optional[Auth]:
        """Get the current authentication strategy."""
        return self._auth

    @auth.setter
    def auth(self, value: Optional[Auth]) -> None:
        """Set a new authentication strategy."""
        self._auth = value


class AsasClient(BaseAsasClient[SyncEngine]):
    """
    Synchronous API client.

    Extra keyword arguments are forwarded to :class:`HTTPXSyncEngine` when no
    ``engine`` is given.
    """

    def __init__(
        self,
        base_url: str = "",
        *,
        engine: Optional[SyncEngine] = None,
        auth: Optional[Auth] = None,
        hooks: Optional[Hooks] = None,
        raise_for_status: bool = True,
        **engine_kwargs: Any,
    ) -> None:
        super().__init__(
            base_url,
            engine or HTTPXSyncEngine(**engine_kwargs),
            auth=auth,
            hooks=hooks,
            raise_for_status=raise_for_status,
        )

    def close(self) -> None:
        """Close the underlying engine (even one supplied by the caller)."""
        self.engine.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class AsasAsyncClient(BaseAsasClient[AsyncEngine]):
    """
    Asynchronous API client.

    Extra keyword arguments are forwarded to :class:`HTTPXAsyncEngine` when no
    ``engine`` is given.
    """

    def __init__(
        self,
        base_url: str = "",
        *,
        engine: Optional[AsyncEngine] = None,
        auth: Optional[Auth] = None,
        hooks: Optional[Hooks] = None,
        raise_for_status: bool = True,
        **engine_kwargs: Any,
    ) -> None:
        super().__init__(
            base_url,
            engine or HTTPXAsyncEngine(**engine_kwargs),
            auth=auth,
            hooks=hooks,
            raise_for_status=raise_for_status,
        )

    async def aclose(self) -> None:
        """Close the underlying engine (even one supplied by the caller)."""
        await self.engine.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
