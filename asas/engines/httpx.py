from typing import Any, Optional

import httpx

from asas.core.models import Payload, Request, Response


class HTTPXEngine:
    """
    HTTPX implementation of the Asas Engine.
    Manages sync and async clients for optimal performance.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.client_config = kwargs
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    @property
    def sync_client(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(**self.client_config)
        return self._sync_client

    @property
    def async_client(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(**self.client_config)
        return self._async_client

    def _prepare_httpx_request(self, request: Request) -> httpx.Request:
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

    def _from_httpx_response(self, response: httpx.Response) -> Response:
        return Response(
            status_code=response.status_code,
            headers=dict(response.headers),
            content=response.content,
            text=response.text,
        )

    def send(self, request: Request) -> Response:
        httpx_req = self._prepare_httpx_request(request)
        # Note: In some versions of httpx, .send() doesn't take timeout.
        # It's usually handled in .request() or via the client's own configuration.
        # If we need per-request timeout, we might need a different approach.
        response = self.sync_client.send(httpx_req)
        return self._from_httpx_response(response)

    async def asend(self, request: Request) -> Response:
        httpx_req = self._prepare_httpx_request(request)
        response = await self.async_client.send(httpx_req)
        return self._from_httpx_response(response)

    def close(self) -> None:
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

    async def aclose(self) -> None:
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
