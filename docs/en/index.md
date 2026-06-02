# Asas

<p align="center">
  <img src="../assets/logo-without-bg.png" alt="Asas Logo" width="300">
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
- **APIKeyAuth**: `APIKeyAuth("your-key", name="X-API-Key", location="header")` (supports `header` or `query`)

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
