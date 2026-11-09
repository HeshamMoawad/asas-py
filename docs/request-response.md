# Request Bodies & Responses

Asas integrates with [Pydantic](https://docs.pydantic.dev/) on both ends of a call: Pydantic
models go **in** as the request body, and the **return annotation** validates what comes
**out**.

## Sending a request body

Any parameter annotated as a Pydantic `BaseModel`, a `list` of them, or a `dict` is
serialized to JSON and sent as the request body:

```python
from pydantic import BaseModel

from asas import AsasClient, post


class CreateUser(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str


class MyClient(AsasClient):
    @post("/users")
    def create_user(self, payload: CreateUser) -> User:
        raise NotImplementedError


client = MyClient(base_url="https://api.example.com")
client.create_user(CreateUser(name="Ada", email="ada@example.com"))
# body: {"name": "Ada", "email": "ada@example.com"}
```

A list of models becomes a JSON array, and a `dict` is sent as a JSON object:

```python
class BulkClient(AsasClient):
    @post("/users/bulk")
    def create_users(self, payload: list[CreateUser]) -> list[User]:
        raise NotImplementedError

    @post("/events")
    def send_event(self, payload: dict[str, str]) -> None:
        raise NotImplementedError
```

The body is dumped in JSON mode and by alias, so `datetime`, `UUID`, `Decimal`, enums and
aliased fields serialize correctly. To control the dump (for example for partial updates),
use the [`Body`](parameters.md#markers) marker:

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, Body, patch


class UserPatch(BaseModel):
    name: str | None = None
    email: str | None = None


class PatchClient(AsasClient):
    @patch("/users/{id}")
    def update_user(
        self, id: int, changes: Annotated[UserPatch, Body(exclude_unset=True)]
    ) -> None:
        raise NotImplementedError
```

For forms, files, headers and cookies see [Parameters](parameters.md).

## Parsing the response

The return annotation decides what you get back:

| Return annotation | Result |
| --- | --- |
| `Response` | the raw [`Response`](models.md#response) |
| `None` | `None`; the body is discarded |
| `bytes` | `response.content` |
| `str` | `response.text` |
| `bytes \| None`, `str \| None` | as above, or `None` for an empty body |
| any other type `T` | `TypeAdapter(T).validate_json(response.content)` |

Because the model path uses a Pydantic `TypeAdapter`, any typing construct works: a single
model, `list[Model]`, `dict[str, Model]`, unions, and so on.

=== "Single model"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get


    class User(BaseModel):
        id: int
        name: str


    class MyClient(AsasClient):
        @get("/users/{id}")
        def get_user(self, id: int) -> User:
            raise NotImplementedError


    client = MyClient(base_url="https://api.example.com")
    user = client.get_user(1)   # -> User(id=1, name="...")
    ```

=== "List of models"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get


    class User(BaseModel):
        id: int
        name: str


    class MyClient(AsasClient):
        @get("/users")
        def get_users(self) -> list[User]:
            raise NotImplementedError
    ```

=== "Raw response"

    ```python
    from asas import AsasClient, Response, get


    class MyClient(AsasClient):
        @get("/health")
        def health(self) -> Response:
            raise NotImplementedError


    client = MyClient(base_url="https://api.example.com")
    response = client.health()
    print(response.status_code, response.json())
    ```

A `-> Response` endpoint never raises on status, so you can inspect any status code yourself.
Every other return type raises a [typed error](errors.md) on a non-2xx response.

### Empty bodies

If the body is empty, an endpoint whose return type admits `None` returns `None`:

```python
from pydantic import BaseModel

from asas import AsasClient, get


class Profile(BaseModel):
    bio: str


class MyClient(AsasClient):
    @get("/users/{id}/profile")
    def profile(self, id: int) -> Profile | None:
        raise NotImplementedError   # e.g. a 204 with no body returns None
```

For any other model type an empty body raises [`ResponseValidationError`](errors.md). A body
that is not valid JSON, or does not match the model, raises it too.

## Combining body and response models

A typical create-and-return endpoint uses both at once, with no extra code:

```python
from pydantic import BaseModel

from asas import AsasClient, post


class CreateUser(BaseModel):
    name: str
    email: str


class User(BaseModel):
    id: int
    name: str
    email: str


class MyClient(AsasClient):
    @post("/users")
    def create_user(self, payload: CreateUser) -> User:
        raise NotImplementedError


client = MyClient(base_url="https://api.example.com")
created = client.create_user(CreateUser(name="Ada", email="ada@example.com"))
# `payload` is sent as the JSON body; the response is validated into `User`.
```

!!! tip "Post-processing"
    The method body is never run, so to reshape a result write an ordinary method that calls
    the endpoint, or use a [hook](hooks.md).
