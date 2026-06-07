# Asas

<p align="center">
  <img src="https://heshammoawad.github.io/asas-py/assets/logo-without-bg.png" alt="Asas Logo" width="300">
</p>

*Asas framework, high performance, easy to learn, fast to code, ready for production*

---

## About

Asas is a streamlined framework designed for building API clients through a clean, decorator-based interface. Engineered for modern Python development, it provides native support for asynchronous operations and seamless integration with Pydantic for robust data validation.

## Goal

The core objective of Asas is to redefine API integration by making it more "Pythonic," elegant, and maintainable. By abstracting the verbosity typically associated with traditional request libraries, Asas empowers developers to focus on clear architecture and expressive code.

## Quick Start

### Installation

```bash
pip install asas-py
```

### Usage

Asas provides separate clients for synchronous and asynchronous operations.

#### Synchronous Client

```python
from asas import AsasClient, get, Response

class MyClient(AsasClient):
    @get("/users/{id}")
    def get_user(self, response: Response, id: int):
        return response.json()

client = MyClient(base_url="https://api.example.com")
user = client.get_user(id=1)
```

#### Asynchronous Client

```python
from asas import AsasAsyncClient, get, Response

class MyAsyncClient(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, response: Response, id: int):
        return response.json()

async def main():
    client = MyAsyncClient(base_url="https://api.example.com")
    user = await client.get_user(id=1)
    await client.engine.aclose()
```

## Features

### Authentication

Asas supports several authentication strategies out of the box:

- **BasicAuth**: `BasicAuth("username", "password")`
- **BearerAuth**: `BearerAuth("your-token")`
- **APIKeyAuth**: `APIKeyAuth("your-key", name="X-API-Key", location=APIKeyLocation.HEADER)` — `location` accepts the `APIKeyLocation` enum (`HEADER` or `QUERY`); a plain `"header"`/`"query"` string is also accepted.

```python
from asas import AsasClient, BearerAuth

auth = BearerAuth("my-secret-token")
client = MyClient(base_url="https://api.example.com", auth=auth)
```

### Automatic Token Refresh

You can use `RefreshingBearerAuth` to automatically refresh tokens when a `401 Unauthorized` response is received.

```python
from asas import AsasAsyncClient, RefreshingBearerAuth

async def refresh_token():
    # Your logic to get a new token
    return "new-token"

auth = RefreshingBearerAuth(
    token="initial-token",
    async_refresh_callback=refresh_token
)

client = MyAsyncClient(base_url="https://api.example.com", auth=auth)
# If a call returns 401, it will automatically refresh and retry once.
```

### Per-Endpoint Auth Control

Disable authentication for specific public endpoints even if the client has a global auth strategy.

```python
class MyClient(AsasClient):
    @get("/public-data", use_auth=False)
    def get_public(self, response: Response):
        return response.json()
```

### Request Bodies & Parameter Routing

When you call a decorated method, Asas inspects each argument and routes it
automatically based on its name and type:

| Argument | Routed to |
| --- | --- |
| Name matches a `{placeholder}` in the path | Substituted into the URL |
| A Pydantic `BaseModel` (or a list of them) | The JSON request body |
| Anything else that isn't `None` | A query parameter |

> **Important:** the request body must be a Pydantic model. A plain `dict` does
> **not** become the body — it is sent as query parameters. Wrap body data in a
> `BaseModel` to send it as JSON.

```python
from pydantic import BaseModel
from asas import AsasClient, post, Response

class CreateUser(BaseModel):
    name: str
    email: str

class MyClient(AsasClient):
    # {id}    -> substituted into the URL
    # payload -> sent as the JSON body (it's a BaseModel)
    # team    -> sent as a query parameter (?team=...)
    @post("/teams/{id}/users")
    def create_user(self, response: Response, id: int, payload: CreateUser, team: str):
        return response.json()

client = MyClient(base_url="https://api.example.com")
client.create_user(id=42, payload=CreateUser(name="Ada", email="ada@example.com"), team="core")
# POST https://api.example.com/teams/42/users?team=core
# body: {"name": "Ada", "email": "ada@example.com"}
```

### Pydantic Integration

Asas seamlessly integrates with Pydantic for request/response validation.

```python
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    id: int
    name: str

class MyClient(AsasClient):
    @get("/users", response_model=List[User])
    def get_users(self, users: List[User]):
        return users
```
