"""Using the optional ``requests`` engine instead of the default ``httpx``.

Install the requests extra first:

    pip install "asas-py[requests]"

The requests engine is synchronous only. Use it with ``AsasClient``; trying to
use it with ``AsasAsyncClient`` raises a ``TypeError``. This example talks to
the public DummyJSON API, so it needs network access.
"""

from typing import List

from pydantic import BaseModel

from asas import AsasClient, get
from asas.engines.requests import RequestsSyncEngine


class User(BaseModel):
    id: int
    firstName: str
    lastName: str


class UsersResponse(BaseModel):
    users: List[User]


class RequestsClient(AsasClient):
    @get("/users")
    def list_users(self) -> UsersResponse:
        raise NotImplementedError


def main() -> None:
    # Pass the requests engine explicitly; httpx stays the installed default.
    with RequestsClient(
        base_url="https://dummyjson.com", engine=RequestsSyncEngine()
    ) as client:
        try:
            users = client.list_users().users
            print(f"Fetched {len(users)} users via the requests engine.")
            if users:
                first = users[0]
                print(f"First user: {first.firstName} {first.lastName} (id={first.id})")
        except Exception as exc:
            print(f"Request via requests engine failed: {exc}")


if __name__ == "__main__":
    main()
