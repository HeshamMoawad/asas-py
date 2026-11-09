import dataclasses
from typing import List

import httpx
import pytest
import respx
from httpx import Response as HttpxResponse
from pydantic import BaseModel

from asas import (
    AsasAsyncClient,
    AsasClient,
    AsasError,
    BearerAuth,
    Hooks,
    NotFoundError,
    RefreshingBearerAuth,
    Request,
    Response,
    ResponseValidationError,
    TransportError,
    get,
)

BASE = "https://api.example.com"


class Item(BaseModel):
    id: int


class Client(AsasClient):
    @get("/thing")
    def thing(self) -> Response:
        raise NotImplementedError

    @get("/item")
    def item(self) -> Item:
        raise NotImplementedError


class AsyncClient(AsasAsyncClient):
    @get("/thing")
    async def thing(self) -> Response:
        raise NotImplementedError


def test_on_request_sees_auth_and_can_replace_request() -> None:
    def add_header(request: Request) -> Request:
        assert request.headers["Authorization"] == "Bearer t"
        return dataclasses.replace(request, headers={**request.headers, "X-Hook": "1"})

    client = Client(BASE, auth=BearerAuth("t"), hooks=Hooks(on_request=[add_header]))
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/thing").mock(return_value=HttpxResponse(200))
        client.thing()
        assert route.calls.last.request.headers["X-Hook"] == "1"


def test_client_hooks_run_before_endpoint_hooks() -> None:
    order: List[str] = []

    class Ordered(AsasClient):
        @get(
            "/thing",
            hooks=Hooks(on_request=[lambda r: order.append("endpoint")]),
        )
        def thing(self) -> Response:
            raise NotImplementedError

    client = Ordered(
        BASE,
        hooks=Hooks(on_request=[lambda r: order.append("client")]),
    )
    with respx.mock(base_url=BASE) as mock:
        mock.get("/thing").mock(return_value=HttpxResponse(200))
        client.thing()
    assert order == ["client", "endpoint"]


def test_on_response_called_with_request_and_response() -> None:
    seen: List[tuple[Request, Response]] = []
    client = Client(
        BASE, hooks=Hooks(on_response=[lambda req, res: seen.append((req, res))])
    )
    with respx.mock(base_url=BASE) as mock:
        mock.get("/thing").mock(return_value=HttpxResponse(201))
        result = client.thing()
    [(request, response)] = seen
    assert request.url == f"{BASE}/thing"
    assert response is result and response.status_code == 201


def _counting_hooks(calls: List[str]) -> Hooks:
    return Hooks(
        on_request=[lambda r: calls.append("request")],
        on_response=[lambda req, res: calls.append("response")],
    )


def test_hooks_rerun_on_refresh_retry() -> None:
    calls: List[str] = []
    auth = RefreshingBearerAuth("old", refresh_callback=lambda: "new")
    client = Client(BASE, auth=auth, hooks=_counting_hooks(calls))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/thing").mock(side_effect=[HttpxResponse(401), HttpxResponse(200)])
        client.thing()
    assert calls == ["request", "response", "request", "response"]


@pytest.mark.asyncio
async def test_hooks_rerun_on_refresh_retry_async() -> None:
    async def arefresh() -> str:
        return "new"

    calls: List[str] = []
    auth = RefreshingBearerAuth("old", async_refresh_callback=arefresh)
    client = AsyncClient(BASE, auth=auth, hooks=_counting_hooks(calls))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/thing").mock(side_effect=[HttpxResponse(401), HttpxResponse(200)])
        await client.thing()
    assert calls == ["request", "response", "request", "response"]
    await client.engine.aclose()


def test_on_error_for_status_error() -> None:
    errors: List[AsasError] = []
    client = Client(BASE, hooks=Hooks(on_error=[errors.append]))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/item").mock(return_value=HttpxResponse(404))
        with pytest.raises(NotFoundError) as exc:
            client.item()
    assert errors == [exc.value]
    assert errors[0] is exc.value


def test_on_error_for_validation_and_transport_errors() -> None:
    errors: List[AsasError] = []
    client = Client(BASE, hooks=Hooks(on_error=[errors.append]))
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/item").mock(
            return_value=HttpxResponse(200, json={"id": "nope"})
        )
        with pytest.raises(ResponseValidationError) as invalid:
            client.item()
        route.mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(TransportError) as transport:
            client.item()
    assert len(errors) == 2
    assert errors[0] is invalid.value
    assert errors[1] is transport.value


@pytest.mark.asyncio
async def test_on_error_for_transport_error_async() -> None:
    errors: List[AsasError] = []
    client = AsyncClient(BASE, hooks=Hooks(on_error=[errors.append]))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/thing").mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(TransportError) as exc:
            await client.thing()
    assert len(errors) == 1 and errors[0] is exc.value
    await client.engine.aclose()


def test_hook_exception_propagates() -> None:
    errors: List[AsasError] = []

    def boom(request: Request) -> None:
        raise RuntimeError("x")

    client = Client(BASE, hooks=Hooks(on_request=[boom], on_error=[errors.append]))
    with respx.mock(base_url=BASE, assert_all_called=False) as mock:
        route = mock.get("/thing").mock(return_value=HttpxResponse(200))
        with pytest.raises(RuntimeError, match="x"):
            client.thing()
        assert not route.called
    assert errors == []


def test_hook_added_during_a_pass_runs_from_the_next_request() -> None:
    ran: List[str] = []

    def late(request: Request) -> None:
        ran.append("late")

    def adder(request: Request) -> None:
        ran.append("adder")
        client.hooks.on_request.append(late)

    client = Client(BASE, hooks=Hooks(on_request=[adder]))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/thing").mock(return_value=HttpxResponse(200))
        client.thing()
        assert ran == ["adder"]
        client.thing()
    assert ran == ["adder", "adder", "late"]
