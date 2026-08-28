from typing import Any

import pytest
import respx
from httpx import Response as HttpxResponse

from asas import (
    AsasClient,
    RefreshingBearerAuth,
    Response,
    get,
    refresh_on_all,
    refresh_on_any,
    refresh_on_json,
    refresh_on_keyword,
    refresh_on_status,
)

BASE = "https://api.example.com"


class Client(AsasClient):
    @get("/protected")
    def call(self, response: Response) -> Response:
        return response


def _client(**auth_kwargs: Any) -> Client:
    auth = RefreshingBearerAuth("old", refresh_callback=lambda: "new", **auth_kwargs)
    return Client(base_url=BASE, auth=auth)


def test_keyword_in_200_body_triggers_refresh() -> None:
    client = _client(refresh_when=refresh_on_keyword("token_expired"))

    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/protected").mock(
            side_effect=[
                HttpxResponse(200, json={"error": "token_expired"}),
                HttpxResponse(200, json={"ok": True}),
            ]
        )

        result = client.call()
        assert result.json() == {"ok": True}
        assert route.call_count == 2
        assert route.calls[0].request.headers["Authorization"] == "Bearer old"
        assert route.calls[1].request.headers["Authorization"] == "Bearer new"


def test_json_key_value_with_status_triggers_refresh() -> None:
    client = _client(
        refresh_when=refresh_on_json("code", "AUTH_EXPIRED", status=200),
    )

    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/protected").mock(
            side_effect=[
                HttpxResponse(200, json={"code": "AUTH_EXPIRED"}),
                HttpxResponse(200, json={"code": "OK"}),
            ]
        )

        client.call()
        assert route.call_count == 2
        assert route.calls[1].request.headers["Authorization"] == "Bearer new"


def test_json_condition_ignores_non_matching_body() -> None:
    client = _client(refresh_when=refresh_on_json("code", "AUTH_EXPIRED", status=200))

    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/protected").mock(
            return_value=HttpxResponse(200, json={"code": "OK"})
        )

        client.call()
        assert route.call_count == 1  # no refresh, no retry


def test_custom_status_code_triggers_refresh() -> None:
    # Some APIs use 419/440 instead of 401 for an expired session.
    client = _client(refresh_when=refresh_on_status(419))

    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/protected").mock(
            side_effect=[HttpxResponse(419), HttpxResponse(200)]
        )

        client.call()
        assert route.call_count == 2
        assert route.calls[1].request.headers["Authorization"] == "Bearer new"


def test_default_condition_still_401_only() -> None:
    client = _client()  # no refresh_when -> default

    with respx.mock(base_url=BASE) as mock:
        # A 200 with an error-looking body must NOT trigger a refresh by default.
        route = mock.get("/protected").mock(
            return_value=HttpxResponse(200, json={"error": "token_expired"})
        )

        client.call()
        assert route.call_count == 1


def test_refresh_on_any_and_all() -> None:
    any_cond = refresh_on_any(refresh_on_status(401), refresh_on_keyword("expired"))
    assert any_cond(Response(401, {}, b"", "")) is True
    assert any_cond(Response(200, {}, b"session expired", "session expired")) is True
    assert any_cond(Response(200, {}, b"fine", "fine")) is False

    all_cond = refresh_on_all(
        refresh_on_status(200), refresh_on_json("needs_refresh", True)
    )
    import json as _json

    body = _json.dumps({"needs_refresh": True}).encode()
    assert all_cond(Response(200, {}, body, body.decode())) is True
    assert all_cond(Response(401, {}, body, body.decode())) is False


def test_subclass_can_override_should_refresh() -> None:
    class HeaderRefreshAuth(RefreshingBearerAuth):
        def should_refresh(self, response: Response) -> bool:
            # Response header names are lowercased.
            return response.headers.get("x-token-expired") == "1"

    auth = HeaderRefreshAuth("old", refresh_callback=lambda: "new")
    client = Client(base_url=BASE, auth=auth)

    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/protected").mock(
            side_effect=[
                HttpxResponse(200, headers={"X-Token-Expired": "1"}),
                HttpxResponse(200),
            ]
        )

        client.call()
        assert route.call_count == 2
        assert route.calls[1].request.headers["Authorization"] == "Bearer new"
