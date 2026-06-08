import base64
import hashlib
import os
import time
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
    runtime_checkable,
)

from asas.core.models import Request, Response


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

    On a ``401`` the client calls :meth:`refresh` / :meth:`arefresh`, rebuilds
    the request and retries it exactly once.
    """

    def refresh(self) -> None:
        """Refresh authentication synchronously."""
        ...

    async def arefresh(self) -> None:
        """Refresh authentication asynchronously."""
        ...


@runtime_checkable
class ChallengeResponseAuth(Auth, Protocol):
    """Protocol for schemes that answer a server challenge (e.g. HTTP Digest).

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


class OAuth2ClientCredentialsAuth(RefreshableAuth):
    """OAuth2 *client credentials* grant.

    Fetches a bearer token from ``token_url`` using the client id/secret and
    attaches it as ``Authorization: Bearer <token>``. The token is fetched
    lazily on first use and refreshed automatically on a ``401`` (or once it
    is known to have expired).

    By default the token request is performed with ``httpx``. Provide
    ``token_fetcher`` / ``async_token_fetcher`` to use a custom transport; each
    receives the request form fields and must return either the access-token
    string or a ``{"access_token": ..., "expires_in": ...}`` mapping.
    """

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: Optional[str] = None,
        token: Optional[str] = None,
        token_prefix: str = "Bearer ",
        token_fetcher: Optional[Callable[[Dict[str, str]], Any]] = None,
        async_token_fetcher: Optional[Callable[[Dict[str, str]], Any]] = None,
    ) -> None:
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.token = token
        self.token_prefix = token_prefix
        self.token_fetcher = token_fetcher
        self.async_token_fetcher = async_token_fetcher
        self._expires_at: Optional[float] = None

    def _form(self) -> Dict[str, str]:
        form = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            form["scope"] = self.scope
        return form

    def _store(self, result: Any) -> None:
        if isinstance(result, dict):
            self.token = result["access_token"]
            expires_in = result.get("expires_in")
            self._expires_at = time.time() + expires_in if expires_in else None
        else:
            self.token = result
            self._expires_at = None

    @property
    def is_expired(self) -> bool:
        if self.token is None:
            return True
        return self._expires_at is not None and time.time() >= self._expires_at

    def apply(self, request: Request) -> Request:
        if self.token:
            request.headers["Authorization"] = f"{self.token_prefix}{self.token}"
        return request

    def refresh(self) -> None:
        if self.token_fetcher:
            self._store(self.token_fetcher(self._form()))
            return
        import httpx

        response = httpx.post(self.token_url, data=self._form())
        response.raise_for_status()
        self._store(response.json())

    async def arefresh(self) -> None:
        if self.async_token_fetcher:
            self._store(await self.async_token_fetcher(self._form()))
            return
        if self.token_fetcher:
            self._store(self.token_fetcher(self._form()))
            return
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=self._form())
        response.raise_for_status()
        self._store(response.json())


class DigestAuth(ChallengeResponseAuth):
    """HTTP Digest Authentication (RFC 7616).

    The first request is sent without credentials; the server replies with a
    ``401`` carrying a ``WWW-Authenticate: Digest ...`` challenge. The client
    feeds that challenge back in via :meth:`handle_challenge`, then rebuilds and
    retries the request — at which point :meth:`apply` can compute the digest.
    Subsequent requests reuse the cached challenge with an incrementing nonce
    count. Supports ``qop=auth`` and the ``MD5``/``SHA-256`` algorithms.
    """

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self._challenge: Optional[Dict[str, str]] = None
        self._nonce_count = 0

    def handle_challenge(self, response: Response) -> bool:
        header = response.headers.get("WWW-Authenticate")
        if header is None:
            header = response.headers.get("www-authenticate", "")
        if not header.strip().lower().startswith("digest"):
            return False
        self._challenge = _parse_challenge(header)
        self._nonce_count = 0
        return True

    def apply(self, request: Request) -> Request:
        if self._challenge is None:
            return request
        request.headers["Authorization"] = self._build_header(request)
        return request

    def _hasher(self) -> Callable[[str], str]:
        algorithm = (self._challenge or {}).get("algorithm", "MD5").upper()
        func = hashlib.sha256 if algorithm.startswith("SHA-256") else hashlib.md5
        return lambda data: func(data.encode("utf-8")).hexdigest()

    def _build_header(self, request: Request) -> str:
        challenge = self._challenge or {}
        realm = challenge.get("realm", "")
        nonce = challenge.get("nonce", "")
        qop = challenge.get("qop")
        opaque = challenge.get("opaque")
        algorithm = challenge.get("algorithm", "MD5")

        uri = _request_uri(request.url)
        h = self._hasher()
        ha1 = h(f"{self.username}:{realm}:{self.password}")
        ha2 = h(f"{request.method}:{uri}")

        params = {
            "username": self.username,
            "realm": realm,
            "nonce": nonce,
            "uri": uri,
            "algorithm": algorithm,
        }

        if qop:
            self._nonce_count += 1
            nc = f"{self._nonce_count:08x}"
            cnonce = os.urandom(8).hex()
            response = h(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
            params.update({"qop": "auth", "nc": nc, "cnonce": cnonce})
        else:
            response = h(f"{ha1}:{nonce}:{ha2}")

        params["response"] = response
        if opaque is not None:
            params["opaque"] = opaque

        unquoted = {"algorithm", "qop", "nc"}
        parts = [
            f"{key}={value}" if key in unquoted else f'{key}="{value}"'
            for key, value in params.items()
        ]
        return "Digest " + ", ".join(parts)


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


def _request_uri(url: str) -> str:
    """Return the request-URI (path plus query) used for the digest A2 term."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    uri = parts.path or "/"
    if parts.query:
        uri = f"{uri}?{parts.query}"
    return uri


def _parse_challenge(header: str) -> Dict[str, str]:
    """Parse a ``WWW-Authenticate: Digest ...`` header into a dict."""
    header = header.strip()
    if header.lower().startswith("digest"):
        header = header[len("digest") :].strip()

    challenge: Dict[str, str] = {}
    for field in _split_challenge(header):
        if "=" not in field:
            continue
        key, _, value = field.partition("=")
        challenge[key.strip()] = value.strip().strip('"')
    return challenge


def _split_challenge(header: str) -> List[str]:
    """Split a challenge on commas that are not inside quoted strings."""
    fields: List[str] = []
    current: List[str] = []
    in_quotes = False
    for char in header:
        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
        elif char == "," and not in_quotes:
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    if current:
        fields.append("".join(current))
    return fields
