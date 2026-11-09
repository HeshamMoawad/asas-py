"""Static typing checks for decorated endpoints (mypy only; not collected by pytest)."""

from typing import Annotated

from pydantic import BaseModel
from typing_extensions import assert_type

from asas import (
    AsasAsyncClient,
    AsasAsyncResource,
    AsasClient,
    AsasResource,
    Query,
    get,
)


class User(BaseModel):
    id: int


class C(AsasClient):
    @get("/users/{id}")
    def get_user(self, id: int, q: Annotated[str | None, Query()] = None) -> User:
        ...


class AC(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, id: int) -> User:
        ...


def check(c: C) -> None:
    assert_type(c.get_user(1), User)
    assert_type(c.get_user(1, q="x"), User)


async def acheck(c: AC) -> None:
    assert_type(await c.get_user(1), User)


def check_ctx() -> None:
    with C() as c:
        assert_type(c, C)


async def acheck_ctx() -> None:
    async with AC() as c:
        assert_type(c, AC)


class Users(AsasResource[User]):
    path = "/users"


class AsyncUsers(AsasAsyncResource[User]):
    path = "/users"


class RC(AsasClient):
    users = Users()


class ARC(AsasAsyncClient):
    users = AsyncUsers()


def check_resource(c: RC) -> None:
    assert_type(c.users.get(1), User)
    assert_type(c.users.list(), list[User])
    assert_type(c.users.create(User(id=1)), User)
    assert_type(c.users.delete(1), None)
    for u in c.users:
        assert_type(u, User)


async def acheck_resource(c: ARC) -> None:
    assert_type(await c.users.get(1), User)
    assert_type(await c.users.list(), list[User])
    assert_type(await c.users.delete(1), None)
    async for u in c.users:
        assert_type(u, User)
