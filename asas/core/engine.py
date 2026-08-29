from typing import Protocol, runtime_checkable

from asas.core.models import Request, Response


@runtime_checkable
class SyncEngine(Protocol):
    """Protocol for synchronous transport engines."""

    def send(self, request: Request) -> Response:
        """Send a synchronous request."""
        ...

    def close(self) -> None:
        """Close the engine and release resources."""
        ...


@runtime_checkable
class AsyncEngine(Protocol):
    """Protocol for asynchronous transport engines."""

    async def asend(self, request: Request) -> Response:
        """Send an asynchronous request."""
        ...

    async def aclose(self) -> None:
        """Close the engine asynchronously and release resources."""
        ...
