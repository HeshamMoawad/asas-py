"""Static typing checks for decorated endpoints (mypy only; not collected by pytest)."""

from typing import Annotated

from pydantic import BaseModel
from typing_extensions import assert_type

from asas import AsasAsyncClient, AsasClient, Query, get


class User(BaseModel):
    id: int


class C(AsasClient):
    @get("/users/{id}")
    def get_user(self, id: int, q: Annotated[str | None, Query()] = None) -> User:
        raise NotImplementedError


class AC(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, id: int) -> User:
        raise NotImplementedError


def check(c: C) -> None:
    assert_type(c.get_user(1), User)
    assert_type(c.get_user(1, q="x"), User)


async def acheck(c: AC) -> None:
    assert_type(await c.get_user(1), User)
