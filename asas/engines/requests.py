from typing import Any, Dict, Optional

import requests

from asas.core.models import Request, Response


class RequestsSyncEngine:
    """
    Synchronous ``requests`` implementation of the Asas Engine.

    .. warning::

        This engine is **synchronous only**. The ``requests`` library has no
        native async support, so there is no ``RequestsAsyncEngine``. Use it
        with ``AsasClient`` (not ``AsasAsyncClient``); an async client will
        raise ``TypeError`` because this engine lacks ``asend``.

    It lazily creates the underlying :class:`requests.Session` and forwards any
    constructor ``**kwargs`` to it.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.session_config = kwargs
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session(**self.session_config)
        return self._session

    def send(self, request: Request) -> Response:
        kwargs = _prepare_requests_kwargs(request)
        response = self.session.request(
            method=request.method, url=request.url, **kwargs
        )
        return _from_requests_response(response)

    def close(self) -> None:
        if self._session:
            self._session.close()
            self._session = None


def _prepare_requests_kwargs(request: Request) -> Dict[str, Any]:
    """Build the ``requests`` keyword arguments from an Asas :class:`Request`."""
    kwargs: Dict[str, Any] = {
        "params": request.params,
        "headers": request.headers,
        "timeout": request.timeout,
    }

    payload = request.payload
    if payload:
        if payload.json is not None:
            kwargs["json"] = payload.json
        elif payload.data is not None:
            kwargs["data"] = payload.data
        elif payload.files is not None:
            kwargs["files"] = payload.files

    return kwargs


def _from_requests_response(response: requests.Response) -> Response:
    return Response(
        status_code=response.status_code,
        headers=dict(response.headers),
        content=response.content,
        text=response.text,
    )
