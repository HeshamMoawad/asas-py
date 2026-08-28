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
    LinkHeaderPaginator,
    OffsetPaginator,
    PageNumberPaginator,
    Response,
    get,
)

BASE = "https://api.example.com"


class User(BaseModel):
    id: int
    name: str


class Role(BaseModel):
    name: str


# --- Resource definitions -------------------------------------------------


class Users(AsasResource):
    path = "/users"
    model = User

    @get("/users/{id}/roles", response_model=list[Role])
    def roles(self, roles: list, id: int) -> list:
        return roles


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
        import json

        assert json.loads(create_route.calls.last.request.content) == {
            "id": 2,
            "name": "Bob",
        }

        updated = client.users.update(2, User(id=2, name="Bobby"))
        assert updated == User(id=2, name="Bobby")
        assert update_route.called

        deleted = client.users.delete(2)
        assert isinstance(deleted, Response)
        assert deleted.status_code == 204
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

    client = C(base_url=BASE)
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


class AsyncUsers(AsasAsyncResource):
    path = "/users"
    model = User
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
