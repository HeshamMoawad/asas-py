from typing import Any, Generic, Optional, TypeVar, Union

from asas.auth import Auth
from asas.core.engine import AsyncEngine, SyncEngine
from asas.engines.httpx import HTTPXAsyncEngine, HTTPXSyncEngine

E = TypeVar("E", SyncEngine, AsyncEngine)


class BaseAsasClient(Generic[E]):
    """
    Base client for building API clients.
    """

    def __init__(
        self,
        base_url: str,
        engine: E,
        auth: Optional[Auth] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.engine: E = engine
        self.auth = auth


class AsasClient(BaseAsasClient[SyncEngine]):
    """
    Synchronous API client.
    """

    def __init__(
        self,
        base_url: str = "",
        engine: Optional[SyncEngine] = None,
        auth: Optional[Auth] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(base_url, engine or HTTPXSyncEngine(**kwargs), auth=auth)


class AsasAsyncClient(BaseAsasClient[AsyncEngine]):
    """
    Asynchronous API client.
    """

    def __init__(
        self,
        base_url: str = "",
        engine: Optional[AsyncEngine] = None,
        auth: Optional[Auth] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(base_url, engine or HTTPXAsyncEngine(**kwargs), auth=auth)
