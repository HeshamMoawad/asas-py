from __future__ import annotations

from typing import Any, Dict

import pytest
import requests

from asas import AsasAsyncClient, Response, get
from asas.core.models import Payload, Request
from asas.engines.requests import RequestsSyncEngine
from asas.errors import TransportError


def _fake_requests_response(
    status_code: int = 200, json: Any = None, headers: Dict[str, str] | None = None
) -> requests.Response:
    """Build a minimal ``requests`` response for mocking."""
    import json as _json

    resp = requests.Response()
    resp.status_code = status_code
    resp.url = "https://api.example.com/test"
    resp.headers.update(headers or {})
    if json is not None:
        resp._content = _json.dumps(json).encode("utf-8")
    else:
        resp._content = b""
    return resp


def test_requests_engine_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    def _fake(self: Any, method: Any, url: Any, **kwargs: Any) -> requests.Response:
        captured["method"] = method
        captured["url"] = url
        captured["kwargs"] = kwargs
        return _fake_requests_response(200, json={"message": "sync-success"})

    monkeypatch.setattr(requests.Session, "request", _fake)

    engine = RequestsSyncEngine()
    response = engine.send(Request(method="GET", url="https://api.example.com/test"))

    assert response.status_code == 200
    assert response.json() == {"message": "sync-success"}
    assert captured["method"] == "GET"
    engine.close()


def test_requests_engine_payload_and_params(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    def _fake(self: Any, method: Any, url: Any, **kwargs: Any) -> requests.Response:
        captured.update(kwargs)
        return _fake_requests_response(201, json={"id": 1})

    monkeypatch.setattr(requests.Session, "request", _fake)

    engine = RequestsSyncEngine()
    request = Request(
        method="POST",
        url="https://api.example.com/users",
        params={"active": True},
        headers={"X-Custom": "abc"},
        payload=Payload(json={"name": "Ada"}),
    )
    response = engine.send(request)

    assert response.status_code == 201
    assert response.json() == {"id": 1}
    assert captured["json"] == {"name": "Ada"}
    assert captured["params"] == {"active": True}
    assert captured["headers"]["X-Custom"] == "abc"
    engine.close()


def test_requests_engine_data_and_files(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    def _fake(self: Any, method: Any, url: Any, **kwargs: Any) -> requests.Response:
        captured.update(kwargs)
        return _fake_requests_response(204)

    monkeypatch.setattr(requests.Session, "request", _fake)

    engine = RequestsSyncEngine()

    data_request = Request(
        method="POST",
        url="https://api.example.com/raw",
        payload=Payload(data=b"raw-body"),
    )
    engine.send(data_request)
    assert captured.get("data") == b"raw-body"

    files_request = Request(
        method="POST",
        url="https://api.example.com/upload",
        payload=Payload(files={"file": ("a.txt", b"content")}),
    )
    engine.send(files_request)
    assert captured.get("files") == {"file": ("a.txt", b"content")}
    engine.close()


def test_requests_engine_converts_response(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake(self: Any, method: Any, url: Any, **kwargs: Any) -> requests.Response:
        return _fake_requests_response(
            200, json={"ok": True}, headers={"X-Server": "requests"}
        )

    monkeypatch.setattr(requests.Session, "request", _fake)

    engine = RequestsSyncEngine()
    response = engine.send(Request(method="GET", url="https://api.example.com/x"))
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert response.headers["X-Server"] == "requests"
    engine.close()


def test_requests_engine_is_sync_only() -> None:
    engine = RequestsSyncEngine()
    assert not hasattr(engine, "asend")
    assert not hasattr(engine, "aclose")
    engine.close()


@pytest.mark.asyncio
async def test_async_client_with_requests_engine_raises_sync_only_error() -> None:
    class AsyncRequestsClient(AsasAsyncClient):
        @get("/protected")
        async def get_protected(self) -> Response:
            raise NotImplementedError

    client = AsyncRequestsClient(
        base_url="https://api.example.com",
        engine=RequestsSyncEngine(),  # type: ignore[arg-type]
    )

    with pytest.raises(TypeError, match="RequestsSyncEngine"):
        await client.get_protected()


def test_requests_engine_sends_cookies_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: Dict[str, Any] = {}

    def _fake(self: Any, method: Any, url: Any, **kwargs: Any) -> requests.Response:
        captured.update(kwargs)
        return _fake_requests_response(200)

    monkeypatch.setattr(requests.Session, "request", _fake)
    RequestsSyncEngine().send(
        Request("GET", "https://api.example.com/x", cookies={"sid": "abc"}, timeout=3)
    )
    assert captured["cookies"] == {"sid": "abc"}
    assert captured["timeout"] == 3


def test_requests_engine_sends_list_json_and_form_with_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Dict[str, Any]] = []

    def _fake(self: Any, method: Any, url: Any, **kwargs: Any) -> requests.Response:
        calls.append(kwargs)
        return _fake_requests_response(200)

    monkeypatch.setattr(requests.Session, "request", _fake)
    engine = RequestsSyncEngine()
    url = "https://api.example.com/x"
    engine.send(Request("POST", url, payload=Payload(json=[{"a": 1}])))
    engine.send(
        Request(
            "POST",
            url,
            payload=Payload(data={"note": "hi"}, files={"f": ("a.txt", b"x")}),
        )
    )
    assert calls[0]["json"] == [{"a": 1}]
    assert calls[1]["data"] == {"note": "hi"}
    assert calls[1]["files"] == {"f": ("a.txt", b"x")}


def test_requests_engine_transport_error_is_wrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake(self: Any, method: Any, url: Any, **kwargs: Any) -> requests.Response:
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(requests.Session, "request", _fake)
    with pytest.raises(TransportError) as exc:
        RequestsSyncEngine().send(Request("GET", "https://api.example.com/x"))
    assert exc.value.request.url == "https://api.example.com/x"
    assert isinstance(exc.value.__cause__, requests.ConnectionError)
