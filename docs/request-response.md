# Request Bodies & Responses

Asas integrates with [Pydantic](https://docs.pydantic.dev/) on both ends of a call: Pydantic
models go **in** as the request body, and `response_model` validates what comes **out**.

## Sending a request body

Any parameter that is a Pydantic `BaseModel` — or a list of them — is serialized to JSON and
sent as the request body:

```python
from pydantic import BaseModel
from asas import AsasClient, post, Response

class CreateUser(BaseModel):
    name: str
    email: str

class MyClient(AsasClient):
    @post("/users")
    def create_user(self, response: Response, payload: CreateUser):
        return response.json()

client = MyClient(base_url="https://api.example.com")
client.create_user(payload=CreateUser(name="Ada", email="ada@example.com"))
# body: {"name": "Ada", "email": "ada@example.com"}
```

A list of models becomes a JSON array:

```python
@post("/users/bulk")
def create_users(self, response: Response, payload: list[CreateUser]):
    return response.json()
```

!!! warning "A `dict` is not a body"
    Only Pydantic models are routed to the body. A plain `dict` argument is treated as query
    parameters instead. Always wrap body data in a `BaseModel`.

## Validating the response

Pass `response_model` to a decorator and Asas validates the response JSON through a Pydantic
[`TypeAdapter`](https://docs.pydantic.dev/latest/concepts/type_adapter/) before handing it
to your method. This supports plain models, `List[Model]`, and other typing constructs:

=== "Single model"

    ```python
    from pydantic import BaseModel
    from asas import AsasClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyClient(AsasClient):
        @get("/users/{id}", response_model=User)
        def get_user(self, user: User, id: int) -> User:
            return user

    client = MyClient(base_url="https://api.example.com")
    user = client.get_user(id=1)   # -> User(id=1, name="...")
    ```

=== "List of models"

    ```python
    from typing import List
    from pydantic import BaseModel
    from asas import AsasClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyClient(AsasClient):
        @get("/users", response_model=List[User])
        def get_users(self, users: List[User]) -> List[User]:
            return users
    ```

When `response_model` is **omitted**, the raw [`Response`](models.md#response) object is
injected instead, and you call `response.json()` yourself.

## Combining body and response models

A typical create-and-return endpoint uses both at once:

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
    @post("/users", response_model=User)
    def create_user(self, user: User, payload: CreateUser) -> User:
        return user

client = MyClient(base_url="https://api.example.com")
created = client.create_user(payload=CreateUser(name="Ada", email="ada@example.com"))
# `payload` is sent as the JSON body; the response is validated into `User`.
```

!!! tip "Empty bodies are fine"
    Because Asas returns the parsed result when your method body returns `None`, the method
    body can be left as a single `return user` (or even just `...`) purely for typing. See
    [the return convention](routing.md#the-return-convention).
