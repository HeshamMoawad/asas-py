import http
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from asas.core.models import Request, Response


class AsasError(Exception):
    """Base class for every error raised by Asas."""


class HTTPStatusError(AsasError):
    """The server answered with a non-2xx status."""

    def __init__(self, request: Request, response: Response) -> None:
        self.request = request
        self.response = response
        self.status_code = response.status_code
        try:
            phrase = http.HTTPStatus(self.status_code).phrase
        except ValueError:
            phrase = ""
        super().__init__(
            f"{request.method} {request.url} → {self.status_code} {phrase}: "
            f"{response.text[:200]}"
        )


class ClientError(HTTPStatusError):
    """4xx fallback."""


class ServerError(HTTPStatusError):
    """5xx fallback."""


class BadRequestError(ClientError):
    """400"""


class UnauthorizedError(ClientError):
    """401"""


class ForbiddenError(ClientError):
    """403"""


class NotFoundError(ClientError):
    """404"""


class ConflictError(ClientError):
    """409"""


class UnprocessableEntityError(ClientError):
    """422"""


class RateLimitError(ClientError):
    """429; ``retry_after`` is seconds to wait, if the server said."""

    def __init__(self, request: Request, response: Response) -> None:
        super().__init__(request, response)
        self.retry_after: float | None = parse_retry_after(
            response.headers.get("Retry-After") or response.headers.get("retry-after")
        )


class InternalServerError(ServerError):
    """500"""


class ServiceUnavailableError(ServerError):
    """503"""


class ResponseValidationError(AsasError):
    """The response body could not be parsed or validated."""

    def __init__(self, response: Response, error: Exception) -> None:
        self.response = response
        self.error = error
        super().__init__(f"Response validation failed: {error}")


class TransportError(AsasError):
    """The request never produced a response (connection, timeout, ...)."""

    def __init__(self, message: str, request: Request) -> None:
        self.request = request
        super().__init__(message)


_STATUS_ERRORS: dict[int, type[HTTPStatusError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
    500: InternalServerError,
    503: ServiceUnavailableError,
}


def error_for_response(request: Request, response: Response) -> HTTPStatusError:
    """Build the most specific ``HTTPStatusError`` for a non-2xx response."""
    status = response.status_code
    cls = _STATUS_ERRORS.get(status)
    if cls is None:
        if 400 <= status < 500:
            cls = ClientError
        elif 500 <= status < 600:
            cls = ServerError
        else:
            cls = HTTPStatusError
    return cls(request, response)


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    """Parse a ``Retry-After`` header (delta-seconds or HTTP-date) to seconds."""
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    return max(0.0, (when - now).total_seconds())
