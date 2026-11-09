# Parameters

By default Asas infers where each parameter goes. When you need control — a header, a cookie,
a form field, a file upload, or a wire name that is not a valid Python identifier — wrap the
annotation in `Annotated[...]` with a **marker**.

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, Header, Query, get


class User(BaseModel):
    id: int
    name: str


class Users(AsasClient):
    @get("/users/{id}")
    def get_user(
        self,
        id: int,
        expand: Annotated[str | None, Query(alias="x-expand")] = None,
        trace: Annotated[str | None, Header("X-Trace")] = None,
    ) -> User: ...
```

## Markers

| Marker | Destination | Notes |
| --- | --- | --- |
| `Path(alias=None)` | URL segment | Value is percent-encoded with `quote(str(v), safe="")` |
| `Query(alias=None)` | Query string | A list or tuple becomes repeated keys (`?tag=a&tag=b`) |
| `Header(alias=None)` | Request headers | Default name: `x_trace` becomes `X-Trace` |
| `Cookie(alias=None)` | `Request.cookies` | |
| `Body(exclude_unset=False, exclude_none=False)` | JSON body | At most one per endpoint |
| `Form(alias=None)` | Form-encoded body | Any number allowed |
| `File(alias=None)` | Multipart body | `bytes`, a binary file object, or `(filename, content, content_type)` |

`alias` sets the exact name used on the wire. `Header`'s alias may be passed positionally
(`Header("X-Trace")`); every other argument is keyword-only. `Body` has no alias.

```python
from typing import Annotated

from asas import AsasClient, Cookie, Header, Query, get


class Api(AsasClient):
    @get("/items")
    def list_items(
        self,
        tags: list[str],
        sort_by: Annotated[str, Query(alias="sort-by")] = "name",
        session: Annotated[str | None, Cookie()] = None,
        request_id: Annotated[str | None, Header()] = None,   # sent as Request-Id
    ) -> list[dict]: ...
```

!!! note "Where the marker goes"
    Asas reads the marker from `Annotated[T, Marker()]`, or from a union of `None` and a single
    `Annotated[...]`. So `Annotated[str | None, Query()]` and `Annotated[str, Query()] | None`
    both work, and in both cases the parameter type is `str | None`. Python 3.10 wraps
    parameters that default to `None` in `Optional[...]`, and Asas handles that too.

## Inference without a marker

When a parameter has no marker, Asas decides from the annotation at decoration time:

1. The name matches a `{placeholder}` in the path: **`Path`**.
2. The annotation (ignoring `Optional`) is a `BaseModel` subclass, `list[BaseModel]`, or
   `dict` / `dict[...]`: **`Body`**.
3. Anything else: **`Query`**.

A parameter with an explicit marker other than `Path` never fills a same-named
`{placeholder}` — it goes where its marker says, and the placeholder then needs its own
`Path` parameter.

## Serialization

Every value is dumped through a Pydantic `TypeAdapter` built from its annotation, in JSON
mode and by alias. That makes `datetime`, `date`, `UUID`, `Decimal`, enums and aliased model
fields work in every location, for example:

```python
from datetime import datetime
from uuid import UUID

from asas import AsasClient, get


class Api(AsasClient):
    @get("/orders/{order_id}")
    def get_order(self, order_id: UUID, since: datetime | None = None) -> dict: ...
```

- `Body` also honours `exclude_unset` and `exclude_none` from its marker.
- Path, query, header, cookie and form scalars are converted to `str`; booleans become
  `"true"` / `"false"`.
- `None` is omitted from the query, headers, cookies and form. A `None` **path** value raises
  `ValueError` at call time.
- `Form` fields alone produce a form-encoded body; `Form` together with `File` produces one
  multipart body.

## Header precedence

When the same header is set in several places, the later source wins (lowest to highest):

1. Client default headers (`AsasClient(headers=...)`, forwarded to the engine)
2. The endpoint's `headers=` argument
3. `Header()` parameters
4. Auth (for example `BearerAuth` writing `Authorization`)

## Uploading a file with a form field and a header

`File`, `Form` and `Header` combine in one method. The form fields and files are sent together
as a single `multipart/form-data` body:

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, File, Form, Header, post


class Document(BaseModel):
    id: int
    title: str


class Documents(AsasClient):
    @post("/documents")
    def upload(
        self,
        file: Annotated[tuple[str, bytes, str], File()],
        title: Annotated[str, Form()],
        idempotency_key: Annotated[str, Header("Idempotency-Key")],
    ) -> Document: ...


client = Documents(base_url="https://api.example.com")
doc = client.upload(
    ("report.pdf", b"%PDF-1.7 ...", "application/pdf"),
    title="Q3 report",
    idempotency_key="b1f6c0a2",
)
```

## Declaration errors

Each of these raises `TypeError` naming the method when the endpoint is compiled:

- A `{placeholder}` has no matching parameter (by name or `Path` alias).
- A `Path` parameter has no matching placeholder.
- More than one `Body` parameter.
- `Body` combined with `Form` or `File`.
- Two parameters resolve to the same wire name in the same location.
- The return annotation is missing (use `-> Response` for the raw response).
- A parameter has no type annotation.
- The endpoint takes `*args` or `**kwargs`.

Endpoints are compiled when the class is defined, so these surface at import time. The one
exception is a type that is not yet defined at that point: compilation is then deferred to the
first call (see [Routing](routing.md#how-parameters-are-routed)).

## `Path` and `pathlib.Path`

Asas's `Path` marker has the same name as `pathlib.Path`. Import it with `from asas import
Path` only if you do not also need `pathlib.Path`; otherwise `import asas` and write
`asas.Path`:

```python
from pathlib import Path
from typing import Annotated

import asas
from asas import AsasClient, get


class Files(AsasClient):
    @get("/files/{name}")
    def stat(self, name: Annotated[str, asas.Path()]) -> dict: ...


def save(target: Path) -> None:
    target.write_bytes(b"")
```
