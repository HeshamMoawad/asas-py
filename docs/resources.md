# Resources & Pagination

A **resource** groups the endpoints for one kind of record (users, orders, …) and attaches
them to a client. Declare a `path` and an optional `model`, and you get the five CRUD
operations **and** lazy pagination for free — while still being able to add custom endpoints
with the usual decorators.

```python
from pydantic import BaseModel
from asas import AsasClient, AsasResource

class User(BaseModel):
    id: int
    name: str

class Users(AsasResource):
    path = "/users"
    model = User

class MyClient(AsasClient):
    users = Users()          # attach the resource to the client

client = MyClient(base_url="https://api.example.com")
client.users.get(1)          # -> User(id=1, name="...")
```

A resource is bound to its client on access, so it shares the client's `base_url`, `engine`,
and `auth` automatically — including [token refresh](authentication.md) on a `401`.

## Generated CRUD

With `path` and `model` set, a sync resource (`AsasResource`) exposes:

| Method | Request | Returns |
| --- | --- | --- |
| `list(**params)` | `GET /users` | `list[model]` (one page) |
| `get(id)` | `GET /users/{id}` | `model` |
| `create(obj)` | `POST /users` | `model` |
| `update(id, obj)` | `PUT /users/{id}` | `model` |
| `delete(id)` | `DELETE /users/{id}` | `Response` |

```python
client.users.list(active=True)               # GET /users?active=True
user = client.users.create(User(id=0, name="Ada"))
user = client.users.update(user.id, user)
client.users.delete(user.id)
```

`create` and `update` accept a Pydantic model (sent as the JSON body); responses are
validated into `model`. If you omit `model`, results come back as raw JSON.

!!! note "`path` is required for CRUD"
    Calling a CRUD method or iterating without a `path` raises a clear `ValueError`. A
    resource with only custom decorated methods does not need one.

## Custom endpoints

Anything outside plain CRUD is just a decorated method on the same class — exactly like on a
client (see [Routing & Parameters](routing.md)):

```python
from typing import List

class Users(AsasResource):
    path = "/users"
    model = User

    @get("/users/{id}/roles", response_model=List[Role])
    def roles(self, roles: List[Role], id: int) -> List[Role]:
        return roles

client.users.roles(id=1)     # GET /users/1/roles
```

## Lazy iteration over every record

Iterating a resource walks **all pages**, fetching each one on demand — you never write the
page loop yourself:

```python
for user in client.users:        # fetches page 1, then 2, … as needed
    print(user.name)
```

It is lazy: pages are requested only as you consume records, so breaking early stops the
fetching too.

```python
# Only the pages needed for the first 10 records are ever requested.
first_ten = [u for _, u in zip(range(10), client.users)]
```

Use `iterate(**params)` to pass query parameters into the iteration:

```python
for user in client.users.iterate(active=True):
    ...
```

## Pagination styles

Set a `paginator` on the resource to match how your API paginates. The default is
page-number pagination; all strategies share the same lazy loop.

=== "Page number"

    ```python
    from asas import PageNumberPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = PageNumberPaginator(page_param="page", size_param="per_page",
                                        page_size=100)
    # GET /users?page=1&per_page=100, then page=2, … until a short page.
    ```

=== "Offset / limit"

    ```python
    from asas import OffsetPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = OffsetPaginator(offset_param="offset", limit_param="limit", limit=100)
    # GET /users?offset=0&limit=100, then offset=100, … until a short page.
    ```

=== "Cursor / token"

    ```python
    from asas import CursorPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = CursorPaginator(cursor_param="cursor", next_key="meta.next_cursor")
    # Reads the next cursor from the response body (dotted paths allowed) and
    # sends it back as ?cursor=…; stops when it is absent.
    ```

=== "Link header"

    ```python
    from asas import LinkHeaderPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = LinkHeaderPaginator()
    # Follows the RFC 5988  Link: <…>; rel="next"  header until there is none.
    ```

### Where the records live in a page

Every paginator finds the list of records in a page automatically: a top-level JSON array is
used as-is, otherwise the first of `data` / `items` / `results`. Override it with
`items_key` (a dotted path) when your API nests them elsewhere:

```python
paginator = PageNumberPaginator(items_key="data.records")
```

### Custom strategies

To support a bespoke scheme, subclass `Paginator` and implement `first_page` and
`next_page`, returning a `PageRequest` (or `None` to stop):

```python
from asas import Paginator, PageRequest
from asas.core.models import Response

class HeaderCountPaginator(Paginator):
    def first_page(self, params):
        page = dict(params); page["page"] = 1
        return PageRequest(params=page)

    def next_page(self, response: Response, previous: PageRequest):
        total = int(response.headers.get("X-Total-Pages", "1"))
        current = int(previous.params["page"])
        if current >= total:
            return None
        page = dict(previous.params); page["page"] = current + 1
        return PageRequest(params=page)
```

## Async resources

`AsasAsyncResource` mirrors the sync resource for `AsasAsyncClient`. CRUD methods are
awaitable and iteration uses `async for`:

```python
from asas import AsasAsyncClient, AsasAsyncResource

class Users(AsasAsyncResource):
    path = "/users"
    model = User

class MyClient(AsasAsyncClient):
    users = Users()

async def main():
    client = MyClient(base_url="https://api.example.com")
    user = await client.users.get(1)
    async for user in client.users:      # lazy, page by page
        print(user.name)
    await client.engine.aclose()
```
