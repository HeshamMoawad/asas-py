from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
from httpx import Response as HttpxResponse

from asas.core.models import Payload, Request
from asas.engines.httpx import HTTPXAsyncEngine, HTTPXSyncEngine
from asas.errors import TransportError

BASE = "https://api.example.com"


@pytest.mark.asyncio
async def test_httpx_engine_async() -> None:
    engine = HTTPXAsyncEngine()
    async with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/test").mock(
            return_value=HttpxResponse(200, json={"message": "async-success"})
        )

        request = Request(method="GET", url="https://api.example.com/test")
        response = await engine.asend(request)

        assert response.status_code == 200
        assert response.json() == {"message": "async-success"}
    await engine.aclose()


def test_httpx_engine_sync() -> None:
    engine = HTTPXSyncEngine()
    with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/test").mock(
            return_value=HttpxResponse(200, json={"message": "sync-success"})
        )

        request = Request(method="GET", url="https://api.example.com/test")
        response = engine.send(request)

        assert response.status_code == 200
        assert response.json() == {"message": "sync-success"}
    engine.close()


def _post(payload: Payload | None = None, **kwargs: Any) -> Request:
    return Request("POST", f"{BASE}/x", payload=payload, **kwargs)


def _sent(request: Request) -> httpx.Request:
    with respx.mock() as mock:
        route = mock.route().mock(return_value=HttpxResponse(200))
        HTTPXSyncEngine().send(request)
        sent: httpx.Request = route.calls.last.request
    return sent


def test_sends_cookies() -> None:
    sent = _sent(Request("GET", f"{BASE}/x", cookies={"sid": "abc"}))
    assert sent.headers["cookie"] == "sid=abc"


def test_sends_list_json() -> None:
    sent = _sent(_post(Payload(json=[{"a": 1}])))
    assert json.loads(sent.content) == [{"a": 1}]


def test_sends_form_fields() -> None:
    sent = _sent(_post(Payload(data={"a": "1"})))
    assert sent.headers["content-type"].startswith("application/x-www-form-urlencoded")
    assert sent.content == b"a=1"


def test_sends_multipart_with_fields() -> None:
    payload = Payload(
        data={"note": "hi"}, files={"file": ("a.txt", b"x", "text/plain")}
    )
    sent = _sent(_post(payload))
    assert sent.headers["content-type"].startswith("multipart/form-data")
    assert b'name="note"' in sent.content
    assert b'filename="a.txt"' in sent.content


def test_sends_raw_bytes() -> None:
    sent = _sent(_post(Payload(data=b"raw")))
    assert sent.content == b"raw"


def test_transport_error_is_wrapped() -> None:
    with respx.mock() as mock:
        mock.route().mock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(TransportError) as exc:
            HTTPXSyncEngine().send(Request("GET", f"{BASE}/x"))
    assert exc.value.request.url == f"{BASE}/x"
    assert isinstance(exc.value.__cause__, httpx.ConnectError)


@pytest.mark.asyncio
async def test_async_transport_error_is_wrapped() -> None:
    engine = HTTPXAsyncEngine()
    with respx.mock() as mock:
        mock.route().mock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(TransportError) as exc:
            await engine.asend(Request("GET", f"{BASE}/x"))
    assert exc.value.request.url == f"{BASE}/x"
    assert isinstance(exc.value.__cause__, httpx.ConnectError)
    await engine.aclose()


@pytest.mark.asyncio
async def test_async_sends_cookies_and_form() -> None:
    engine = HTTPXAsyncEngine()
    with respx.mock() as mock:
        route = mock.route().mock(return_value=HttpxResponse(200))
        await engine.asend(_post(Payload(data={"a": "1"}), cookies={"sid": "abc"}))
        sent = route.calls.last.request
    assert sent.headers["cookie"] == "sid=abc"
    assert sent.content == b"a=1"
    await engine.aclose()


def test_httpx_timeout_is_forwarded() -> None:
    captured: list[httpx.Request] = []

    def side_effect(request: httpx.Request) -> HttpxResponse:
        captured.append(request)
        return HttpxResponse(200)

    with respx.mock() as mock:
        mock.route().mock(side_effect=side_effect)
        HTTPXSyncEngine().send(Request("GET", f"{BASE}/x", timeout=2.5))
    assert captured[0].extensions["timeout"]["read"] == 2.5
