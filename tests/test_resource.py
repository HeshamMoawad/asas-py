import json
from datetime import datetime
from typing import Any

import pytest
import respx
from httpx import Response as HttpxResponse
from pydantic import BaseModel

from asas import (
    AsasAsyncClient,
    AsasAsyncResource,
    AsasClient,
    AsasResource,
    BearerAuth,
    CursorPaginator,
    Hooks,
    LinkHeaderPaginator,
    NotFoundError,
    OffsetPaginator,
    PageNumberPaginator,
    ResponseValidationError,
    get,
)

BASE = "https://api.example.com"


class User(BaseModel):
    id: int
    name: str


class Role(BaseModel):
    name: str


# --- Resource definitions -------------------------------------------------


class Users(AsasResource[User]):
    path = "/users"

    @get("/users/{id}/roles")
    def roles(self, id: int) -> list[Role]:
        raise NotImplementedError


class StoreClient(AsasClient):
    users = Users()


# --- Binding --------------------------------------------------------------


def test_resource_is_bound_to_client() -> None:
    client = StoreClient(base_url=BASE, auth=BearerAuth("tok"))
    # Same bound instance is reused; it shares the client's config.
    assert client.users is client.users
    assert client.users.base_url == BASE
    assert client.users.auth is client.auth


def test_two_clients_get_independent_bindings() -> None:
    c1 = StoreClient(base_url=BASE)
    c2 = StoreClient(base_url="https://other.example.com")
    assert c1.users is not c2.users
    assert c2.users.base_url == "https://other.example.com"


# --- CRUD -----------------------------------------------------------------


def test_crud_operations() -> None:
    client = StoreClient(base_url=BASE)

    with respx.mock(base_url=BASE) as mock:
        list_route = mock.get("/users").mock(
            return_value=HttpxResponse(200, json=[{"id": 1, "name": "Ada"}])
        )
        get_route = mock.get("/users/1").mock(
            return_value=HttpxResponse(200, json={"id": 1, "name": "Ada"})
        )
        create_route = mock.post("/users").mock(
            return_value=HttpxResponse(201, json={"id": 2, "name": "Bob"})
        )
        update_route = mock.put("/users/2").mock(
            return_value=HttpxResponse(200, json={"id": 2, "name": "Bobby"})
        )
        delete_route = mock.delete("/users/2").mock(return_value=HttpxResponse(204))

        listed = client.users.list()
        assert listed == [User(id=1, name="Ada")]
        assert list_route.called

        fetched = client.users.get(1)
        assert fetched == User(id=1, name="Ada")
        assert get_route.called

        created = client.users.create(User(id=2, name="Bob"))
        assert created == User(id=2, name="Bob")
        assert json.loads(create_route.calls.last.request.content) == {
            "id": 2,
            "name": "Bob",
        }

        updated = client.users.update(2, User(id=2, name="Bobby"))
        assert updated == User(id=2, name="Bobby")
        assert update_route.called

        assert client.users.delete(2) is None  # type: ignore[func-returns-value]
        assert delete_route.called


def test_resource_custom_endpoint_and_auth() -> None:
    client = StoreClient(base_url=BASE, auth=BearerAuth("tok"))

    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/users/1/roles").mock(
            return_value=HttpxResponse(200, json=[{"name": "admin"}])
        )

        roles = client.users.roles(id=1)
        assert roles == [Role(name="admin")]
        assert route.calls.last.request.headers["Authorization"] == "Bearer tok"


def test_crud_requires_path() -> None:
    class Bare(AsasResource):
        pass

    class C(AsasClient):
        things = Bare()

    client = C(base_url=BASE)
    with pytest.raises(ValueError, match="needs a `path`"):
        client.things.list()


# --- Pagination -----------------------------------------------------------


def _pages(*payloads: object) -> list:
    return [HttpxResponse(200, json=p) for p in payloads]


def test_page_number_pagination_default() -> None:
    class PagedUsers(AsasResource):
        path = "/users"
        model = User
        paginator = PageNumberPaginator(page_size=2)

    class C(AsasClient):
        users = PagedUsers()

    client = C(base_url=BASE, auth=BearerAuth("tok"))
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/users").mock(
            side_effect=_pages(
                [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
                [{"id": 3, "name": "c"}, {"id": 4, "name": "d"}],
                [{"id": 5, "name": "e"}],  # short page -> stop
            )
        )

        users = list(client.users)
        assert [u.id for u in users] == [1, 2, 3, 4, 5]
        assert route.call_count == 3
        # Page numbers advance.
        assert route.calls[0].request.url.params["page"] == "1"
        assert route.calls[1].request.url.params["page"] == "2"
        # Auth is applied on every page, not just the first.
        for call in route.calls:
            assert call.request.headers["Authorization"] == "Bearer tok"


def test_iteration_is_lazy() -> None:
    class PagedUsers(AsasResource):
        path = "/users"
        model = User
        paginator = PageNumberPaginator(page_size=2)

    class C(AsasClient):
        users = PagedUsers()

    client = C(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/users").mock(
            side_effect=_pages(
                [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
                [{"id": 3, "name": "c"}],
            )
        )

        it = iter(client.users)
        next(it)  # first record -> only the first page fetched
        assert route.call_count == 1
        next(it)  # second record from page 1, still one fetch
        assert route.call_count == 1
        next(it)  # crosses into page 2
        assert route.call_count == 2


def test_offset_pagination() -> None:
    class OffsetUsers(AsasResource):
        path = "/users"
        model = User
        paginator = OffsetPaginator(limit=2)

    class C(AsasClient):
        users = OffsetUsers()

    client = C(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/users").mock(
            side_effect=_pages(
                [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
                [{"id": 3, "name": "c"}],
            )
        )

        users = list(client.users)
        assert [u.id for u in users] == [1, 2, 3]
        assert route.calls[0].request.url.params["offset"] == "0"
        assert route.calls[1].request.url.params["offset"] == "2"


def test_cursor_pagination_with_items_key() -> None:
    class CursorUsers(AsasResource):
        path = "/users"
        model = User
        paginator = CursorPaginator()  # items auto-detected from "results"

    class C(AsasClient):
        users = CursorUsers()

    client = C(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/users").mock(
            side_effect=_pages(
                {"results": [{"id": 1, "name": "a"}], "next_cursor": "c2"},
                {"results": [{"id": 2, "name": "b"}], "next_cursor": None},
            )
        )

        users = list(client.users)
        assert [u.id for u in users] == [1, 2]
        assert route.call_count == 2
        assert route.calls[1].request.url.params["cursor"] == "c2"


def test_link_header_pagination() -> None:
    class LinkUsers(AsasResource):
        path = "/users"
        model = User
        paginator = LinkHeaderPaginator()

    class C(AsasClient):
        users = LinkUsers()

    client = C(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        route = mock.get("/users").mock(
            side_effect=[
                HttpxResponse(
                    200,
                    json=[{"id": 1, "name": "a"}],
                    headers={"Link": f'<{BASE}/users?page=2>; rel="next"'},
                ),
                HttpxResponse(200, json=[{"id": 2, "name": "b"}]),  # no Link -> stop
            ]
        )

        users = list(client.users)
        assert [u.id for u in users] == [1, 2]
        assert route.call_count == 2


def test_iteration_without_model_yields_raw_dicts() -> None:
    class RawUsers(AsasResource):
        path = "/users"
        paginator = PageNumberPaginator(page_size=2)

    class C(AsasClient):
        users = RawUsers()

    client = C(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/users").mock(
            side_effect=_pages([{"id": 1, "name": "a"}])  # short page -> stop
        )

        users = list(client.users)
        assert users == [{"id": 1, "name": "a"}]


# --- Async ----------------------------------------------------------------


class AsyncUsers(AsasAsyncResource[User]):
    path = "/users"
    paginator = PageNumberPaginator(page_size=2)


class AsyncStoreClient(AsasAsyncClient):
    users = AsyncUsers()


@pytest.mark.asyncio
async def test_async_resource_get_and_iterate() -> None:
    client = AsyncStoreClient(base_url=BASE)

    with respx.mock(base_url=BASE) as mock:
        mock.get("/users/1").mock(
            return_value=HttpxResponse(200, json={"id": 1, "name": "Ada"})
        )
        mock.get("/users").mock(
            side_effect=_pages(
                [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
                [{"id": 3, "name": "c"}],
            )
        )

        one = await client.users.get(1)
        assert one == User(id=1, name="Ada")

        collected = [user async for user in client.users]
        assert [u.id for u in collected] == [1, 2, 3]

    await client.engine.aclose()


# --- Generics, errors, hooks (v0.2) -----------------------------------------


class Admin(BaseModel):
    id: int
    level: int


def test_model_inferred_from_generic() -> None:
    assert Users.model is User


def test_explicit_model_overrides_generic() -> None:
    class X(AsasResource[User]):
        path = "/x"
        model = Admin

    assert X.model is Admin


def test_constructor_model_overrides_generic() -> None:
    assert AsasResource[User](path="/x", model=Admin).model is Admin


def test_bare_resource_returns_raw_json() -> None:
    class Raw(AsasResource):
        path = "/raw"

    class C(AsasClient):
        raw = Raw()

    assert Raw.model is None
    with respx.mock(base_url=BASE) as mock:
        mock.get("/raw/1").mock(return_value=HttpxResponse(200, json={"a": 1}))
        assert C(base_url=BASE).raw.get(1) == {"a": 1}


def test_delete_returns_none() -> None:
    client = StoreClient(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.delete("/users/1").mock(return_value=HttpxResponse(204))
        assert client.users.delete(1) is None  # type: ignore[func-returns-value]


def test_delete_raises_on_error() -> None:
    client = StoreClient(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.delete("/users/1").mock(return_value=HttpxResponse(404))
        with pytest.raises(NotFoundError):
            client.users.delete(1)


def test_crud_raises_typed_errors() -> None:
    client = StoreClient(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/users/99").mock(return_value=HttpxResponse(404))
        with pytest.raises(NotFoundError):
            client.users.get(99)


def test_crud_fires_client_hooks() -> None:
    seen: list = []
    hooks = Hooks(on_request=[lambda req: seen.append(req.url)])
    client = StoreClient(base_url=BASE, hooks=hooks)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/users").mock(return_value=HttpxResponse(200, json=[]))
        client.users.list()
    assert seen == [f"{BASE}/users"]


def test_invalid_record_raises_response_validation_error_and_fires_on_error() -> None:
    errors: list = []
    client = StoreClient(base_url=BASE, hooks=Hooks(on_error=[errors.append]))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/users/1").mock(return_value=HttpxResponse(200, json={"id": "x"}))
        with pytest.raises(ResponseValidationError):
            client.users.get(1)
    assert len(errors) == 1
    assert isinstance(errors[0], ResponseValidationError)


def test_invalid_json_raises_response_validation_error() -> None:
    client = StoreClient(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/users/1").mock(return_value=HttpxResponse(200, content=b"nope"))
        with pytest.raises(ResponseValidationError):
            client.users.get(1)


def test_invalid_page_item_during_iteration_raises_and_fires_on_error() -> None:
    errors: list = []
    client = StoreClient(base_url=BASE, hooks=Hooks(on_error=[errors.append]))
    with respx.mock(base_url=BASE) as mock:
        mock.get("/users").mock(
            return_value=HttpxResponse(200, json=[{"id": 1, "name": "a"}, {"id": 2}])
        )
        with pytest.raises(ResponseValidationError):
            list(client.users)
    assert len(errors) == 1


class Event(BaseModel):
    at: datetime


def test_create_body_is_json_safe() -> None:
    class Events(AsasResource[Event]):
        path = "/events"

    class C(AsasClient):
        events = Events()

    client = C(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        route = mock.post("/events").mock(
            return_value=HttpxResponse(201, json={"at": "2024-01-02T03:04:05"})
        )
        client.events.create(Event(at=datetime(2024, 1, 2, 3, 4, 5)))
        sent: Any = json.loads(route.calls.last.request.content)
    assert sent == {"at": "2024-01-02T03:04:05"}


@pytest.mark.asyncio
async def test_async_resource_generic_and_errors() -> None:
    assert AsyncUsers.model is User
    client = AsyncStoreClient(base_url=BASE)
    with respx.mock(base_url=BASE) as mock:
        mock.get("/users/99").mock(return_value=HttpxResponse(404))
        mock.get("/users/1").mock(return_value=HttpxResponse(200, json={"id": "x"}))
        mock.delete("/users/2").mock(return_value=HttpxResponse(204))
        with pytest.raises(NotFoundError):
            await client.users.get(99)
        with pytest.raises(ResponseValidationError):
            await client.users.get(1)
        assert await client.users.delete(2) is None  # type: ignore[func-returns-value]
    await client.engine.aclose()


def test_inherited_explicit_model_not_overridden_by_parent_generic() -> None:
    class X(AsasResource[User]):
        path = "/x"
        model = Admin

    class Y(X):
        pass

    assert Y.model is Admin


def test_plain_subclass_inherits_generic_model() -> None:
    class Admins(Users):
        pass

    assert Admins.model is User
