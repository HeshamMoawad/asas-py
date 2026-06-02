from typing import Any, Optional

import httpx

from asas.core.models import Payload, Request, Response


class HTTPXSyncEngine:
    """
    Synchronous HTTPX implementation of the Asas Engine.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.client_config = kwargs
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(**self.client_config)
        return self._client

    def _prepare_httpx_request(self, request: Request) -> httpx.Request:
        return _prepare_httpx_request(request)

    def _from_httpx_response(self, response: httpx.Response) -> Response:
        return _from_httpx_response(response)

    def send(self, request: Request) -> Response:
        httpx_req = self._prepare_httpx_request(request)
        response = self.client.send(httpx_req)
        return self._from_httpx_response(response)

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None


class HTTPXAsyncEngine:
    """
    Asynchronous HTTPX implementation of the Asas Engine.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.client_config = kwargs
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(**self.client_config)
        return self._client

    def _prepare_httpx_request(self, request: Request) -> httpx.Request:
        return _prepare_httpx_request(request)

    def _from_httpx_response(self, response: httpx.Response) -> Response:
        return _from_httpx_response(response)

    async def asend(self, request: Request) -> Response:
        httpx_req = self._prepare_httpx_request(request)
        response = await self.client.send(httpx_req)
        return self._from_httpx_response(response)

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


def _prepare_httpx_request(request: Request) -> httpx.Request:
    data = None
    json_payload = None
    files = None

    if request.payload:
        data = request.payload.data
        json_payload = request.payload.json
        files = request.payload.files

    return httpx.Request(
        method=request.method,
        url=request.url,
        params=request.params,
        headers=request.headers,
        content=data if not json_payload and not files else None,
        json=json_payload,
        files=files,
    )


def _from_httpx_response(response: httpx.Response) -> Response:
    return Response(
        status_code=response.status_code,
        headers=dict(response.headers),
        content=response.content,
        text=response.text,
    )
