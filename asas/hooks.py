"""Observation and mutation points around every request the pipeline sends."""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from asas.core.models import Request, Response
from asas.errors import AsasError

RequestHook = Callable[[Request], Optional[Request]]
ResponseHook = Callable[[Request, Response], None]
ErrorHook = Callable[[AsasError], None]


@dataclass
class Hooks:
    """Plain synchronous callables run by the request pipeline.

    Hooks work with sync and async clients alike, so they must not block on I/O.
    ``on_request`` may mutate the request and return ``None``, or return a
    replacement. ``on_error`` only observes: the error is raised afterwards.
    Each pass runs a snapshot of the list, so a hook added during a pass runs
    from the next request on.
    """

    on_request: List[RequestHook] = field(default_factory=list)
    on_response: List[ResponseHook] = field(default_factory=list)
    on_error: List[ErrorHook] = field(default_factory=list)

    def merged(self, other: "Optional[Hooks]") -> "Hooks":
        """Combine hooks: ``self``'s callables run first, then ``other``'s."""
        if other is None:
            return self
        return Hooks(
            on_request=[*self.on_request, *other.on_request],
            on_response=[*self.on_response, *other.on_response],
            on_error=[*self.on_error, *other.on_error],
        )

    def apply_request(self, request: Request) -> Request:
        for hook in list(self.on_request):
            replacement = hook(request)
            if replacement is not None:
                request = replacement
        return request

    def notify_response(self, request: Request, response: Response) -> None:
        for hook in list(self.on_response):
            hook(request, response)

    def notify_error(self, error: AsasError) -> None:
        for hook in list(self.on_error):
            hook(error)
