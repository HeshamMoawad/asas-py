from typing import Protocol, runtime_checkable

from asas.core.models import Request, Response


@runtime_checkable
class Engine(Protocol):
    """
    Protocol for the underlying transport engine.
    Supports both synchronous and asynchronous communication.
    """

    def send(self, request: Request) -> Response:
        """Send a synchronous request."""
        ...

    async def asend(self, request: Request) -> Response:
        """Send an asynchronous request."""
        ...

    def close(self) -> None:
        """Close the engine and release resources."""
        ...

    async def aclose(self) -> None:
        """Close the engine asynchronously and release resources."""
        ...
