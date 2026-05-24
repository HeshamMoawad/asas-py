from typing import List

import pytest
import respx
from httpx import Response as HttpxResponse
from pydantic import BaseModel

from asas import AsasClient, get, post


class Item(BaseModel):
    id: int
    name: str


class User(BaseModel):
    id: int
    username: str
    items: List[Item]


class PydanticClient(AsasClient):
    @get("/items/{item_id}", response_model=Item)
    def get_item(self, item: Item, item_id: int) -> Item:
        return item

    @get("/users/{user_id}", response_model=User)
    async def get_user_async(self, user: User, user_id: int) -> User:
        return user

    @get("/items", response_model=List[Item])
    def list_items(self, items: List[Item]) -> List[Item]:
        return items

    @get("/search", response_model=List[Item])
    def search_items(self, items: List[Item], q: str, limit: int = 10) -> List[Item]:
        # Result is auto-returned if we don't return anything
        return items

    @post("/items", response_model=Item)
    def create_item(self, item: Item, data: Item) -> Item:
        return item


def test_pydantic_sync_parse() -> None:
    client = PydanticClient(base_url="https://api.example.com")
    item_data = {"id": 1, "name": "Test Item"}

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/items/1").mock(return_value=HttpxResponse(200, json=item_data))

        result = client.get_item(item_id=1)
        assert isinstance(result, Item)
        assert result.id == 1
        assert result.name == "Test Item"


@pytest.mark.asyncio
async def test_pydantic_async_parse() -> None:
    client = PydanticClient(base_url="https://api.example.com")
    user_data = {
        "id": 10,
        "username": "johndoe",
        "items": [{"id": 1, "name": "Item 1"}],
    }

    async with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/users/10").mock(
            return_value=HttpxResponse(200, json=user_data)
        )

        result = await client.get_user_async(user_id=10)
        assert isinstance(result, User)
        assert result.id == 10
        assert len(result.items) == 1
    await client.engine.aclose()


def test_pydantic_list_parse() -> None:
    client = PydanticClient(base_url="https://api.example.com")
    items_data = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        respx_mock.get("/items").mock(return_value=HttpxResponse(200, json=items_data))

        result = client.list_items()
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], Item)
        assert result[1].name == "Item 2"


def test_query_params_mapping() -> None:
    client = PydanticClient(base_url="https://api.example.com")
    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # Check that q and limit are passed as query params
        respx_mock.get("/search?q=test&limit=5").mock(
            return_value=HttpxResponse(200, json=[])
        )
        result = client.search_items(q="test", limit=5)
        assert result == []


def test_body_mapping() -> None:
    client = PydanticClient(base_url="https://api.example.com")
    item_to_create = Item(id=100, name="New Item")

    with respx.mock(base_url="https://api.example.com") as respx_mock:
        # Check that the Item object is passed as JSON body
        route = respx_mock.post("/items").mock(
            return_value=HttpxResponse(201, json=item_to_create.model_dump())
        )
        result = client.create_item(data=item_to_create)

        assert route.called
        assert route.calls.last.request.content == b'{"id":100,"name":"New Item"}'
        assert isinstance(result, Item)
        assert result.id == 100
