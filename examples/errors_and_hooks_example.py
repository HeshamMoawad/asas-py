"""Typed errors, ``raise_for_status``, the ``-> Response`` opt-out and hooks.

Runs offline: respx plays a server that rate-limits, 404s and fails.
"""

from typing import Any, Dict, List

import httpx
import respx
from pydantic import BaseModel

from asas import (
    AsasClient,
    AsasError,
    Hooks,
    HTTPStatusError,
    NotFoundError,
    RateLimitError,
    Response,
    get,
)

BASE_URL = "https://api.example.com"


class Item(BaseModel):
    id: int
    name: str


class ItemsClient(AsasClient):
    @get("/items/{id}")
    def get_item(self, id: int) -> Item:
        """Non-2xx raises a typed error (404 -> NotFoundError, 429 -> RateLimitError)."""
        raise NotImplementedError

    @get("/items/{id}", raise_for_status=False)
    def get_item_unchecked(self, id: int) -> Dict[str, Any]:
        """Per-endpoint opt-out: no status check, the error body is just parsed."""
        raise NotImplementedError

    @get("/items/{id}")
    def get_item_raw(self, id: int) -> Response:
        """``-> Response`` returns the raw response and never raises on status."""
        raise NotImplementedError

    @get("/items")
    def list_items(self) -> List[Item]:
        raise NotImplementedError


def main() -> None:
    # on_error hooks only observe: the error is still raised afterwards.
    error_counts: Dict[str, int] = {}

    def count_error(error: AsasError) -> None:
        name = type(error).__name__
        error_counts[name] = error_counts.get(name, 0) + 1

    hooks = Hooks(on_error=[count_error])

    with (
        ItemsClient(base_url=BASE_URL, hooks=hooks) as client,
        respx.mock(base_url=BASE_URL) as server,
    ):
        server.get("/items/1").mock(
            return_value=httpx.Response(200, json={"id": 1, "name": "ok"})
        )
        server.get("/items/2").mock(
            return_value=httpx.Response(
                429, headers={"Retry-After": "30"}, json={"error": "slow down"}
            )
        )
        server.get("/items/3").mock(
            return_value=httpx.Response(404, json={"error": "gone"})
        )
        server.get("/items/4").mock(
            return_value=httpx.Response(200, json={"id": "oops"})
        )
        server.get("/items").mock(return_value=httpx.Response(500, text="boom"))

        print(f"ok: {client.get_item(1)}")

        # RateLimitError carries the parsed Retry-After value, in seconds.
        try:
            client.get_item(2)
        except RateLimitError as exc:
            print(f"rate limited: retry after {exc.retry_after}s")

        try:
            client.get_item(3)
        except NotFoundError as exc:
            print(f"not found: {exc.response.json()}")

        # Opt-outs: raise_for_status=False parses the 404 body as usual, and
        # -> Response hands back the raw response to inspect yourself.
        print(f"unchecked: {client.get_item_unchecked(3)}")
        raw = client.get_item_raw(3)
        print(f"raw response: HTTP {raw.status_code}, no exception")

        # A 2xx body that is not an Item raises ResponseValidationError,
        # which is also an AsasError.
        try:
            client.get_item(4)
        except AsasError as exc:
            print(f"bad body: {type(exc).__name__}")

        # Catch the whole family of status errors at once.
        try:
            client.list_items()
        except HTTPStatusError as exc:
            print(f"server error: {type(exc).__name__} ({exc.status_code})")

    print(f"on_error metrics: {error_counts}")
    print("(AsasClient(raise_for_status=False) turns the checks off client-wide.)")


if __name__ == "__main__":
    main()
