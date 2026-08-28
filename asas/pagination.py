"""Pagination strategies that drive lazy iteration over a resource.

A :class:`Paginator` answers two questions for the resource loop:

* **Where do the records live in a page?** — :meth:`Paginator.extract_items`.
* **What is the next page (if any)?** — :meth:`Paginator.next_page`.

The resource owns the actual HTTP calls; the paginator only decides *how* to
walk pages, so the same strategy works for both the sync and async resources.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from asas.core.models import Response


@dataclass
class PageRequest:
    """The query parameters (or absolute URL) for one page fetch."""

    params: Dict[str, Any] = field(default_factory=dict)
    # When set, the resource fetches this absolute URL verbatim instead of
    # joining ``base_url`` + resource path with ``params`` (used by Link headers).
    url: Optional[str] = None


def _dig(data: Any, dotted_key: str) -> Any:
    """Look up a possibly nested key like ``"meta.next_cursor"`` in a mapping."""
    current = data
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


class Paginator:
    """Base paginator. Subclasses decide how to advance between pages.

    ``items_key`` names where the list of records lives in a page body. When it
    is ``None`` the paginator auto-detects: a top-level JSON array is used as-is,
    otherwise the first of ``data`` / ``items`` / ``results`` that is present.
    """

    def __init__(self, items_key: Optional[str] = None) -> None:
        self.items_key = items_key

    def extract_items(self, response: Response) -> List[Any]:
        data = response.json()
        if self.items_key is not None:
            found = _dig(data, self.items_key)
            return list(found) if found else []
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "items", "results"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
        return []

    def first_page(self, params: Dict[str, Any]) -> PageRequest:
        """Return the request for the first page."""
        return PageRequest(params=dict(params))

    def next_page(
        self, response: Response, previous: PageRequest
    ) -> Optional[PageRequest]:
        """Return the next page request, or ``None`` when iteration is done."""
        raise NotImplementedError


class PageNumberPaginator(Paginator):
    """``?page=1&per_page=100`` style pagination.

    Stops when a page returns fewer records than ``page_size``.
    """

    def __init__(
        self,
        page_param: str = "page",
        size_param: str = "per_page",
        page_size: int = 100,
        start_page: int = 1,
        items_key: Optional[str] = None,
    ) -> None:
        super().__init__(items_key)
        self.page_param = page_param
        self.size_param = size_param
        self.page_size = page_size
        self.start_page = start_page

    def first_page(self, params: Dict[str, Any]) -> PageRequest:
        page = dict(params)
        page[self.page_param] = self.start_page
        page[self.size_param] = self.page_size
        return PageRequest(params=page)

    def next_page(
        self, response: Response, previous: PageRequest
    ) -> Optional[PageRequest]:
        if len(self.extract_items(response)) < self.page_size:
            return None
        page = dict(previous.params)
        page[self.page_param] = int(page[self.page_param]) + 1
        return PageRequest(params=page)


class OffsetPaginator(Paginator):
    """``?offset=0&limit=100`` style pagination.

    Stops when a page returns fewer records than ``limit``.
    """

    def __init__(
        self,
        offset_param: str = "offset",
        limit_param: str = "limit",
        limit: int = 100,
        start: int = 0,
        items_key: Optional[str] = None,
    ) -> None:
        super().__init__(items_key)
        self.offset_param = offset_param
        self.limit_param = limit_param
        self.limit = limit
        self.start = start

    def first_page(self, params: Dict[str, Any]) -> PageRequest:
        page = dict(params)
        page[self.offset_param] = self.start
        page[self.limit_param] = self.limit
        return PageRequest(params=page)

    def next_page(
        self, response: Response, previous: PageRequest
    ) -> Optional[PageRequest]:
        if len(self.extract_items(response)) < self.limit:
            return None
        page = dict(previous.params)
        page[self.offset_param] = int(page[self.offset_param]) + self.limit
        return PageRequest(params=page)


class CursorPaginator(Paginator):
    """Cursor / next-token pagination.

    Reads the next cursor from the response body at ``next_key`` (which may be a
    dotted path like ``"meta.next_cursor"``) and sends it back as the
    ``cursor_param`` query parameter. Stops when the cursor is absent or falsy.
    """

    def __init__(
        self,
        cursor_param: str = "cursor",
        next_key: str = "next_cursor",
        page_size: Optional[int] = None,
        size_param: str = "limit",
        items_key: Optional[str] = None,
    ) -> None:
        super().__init__(items_key)
        self.cursor_param = cursor_param
        self.next_key = next_key
        self.page_size = page_size
        self.size_param = size_param

    def first_page(self, params: Dict[str, Any]) -> PageRequest:
        page = dict(params)
        if self.page_size is not None:
            page[self.size_param] = self.page_size
        return PageRequest(params=page)

    def next_page(
        self, response: Response, previous: PageRequest
    ) -> Optional[PageRequest]:
        cursor = _dig(response.json(), self.next_key)
        if not cursor:
            return None
        page = dict(previous.params)
        page[self.cursor_param] = cursor
        return PageRequest(params=page)


class LinkHeaderPaginator(Paginator):
    """RFC 5988 ``Link: <…>; rel="next"`` header pagination.

    Follows the ``next`` link verbatim until the header no longer offers one.
    """

    def next_page(
        self, response: Response, previous: PageRequest
    ) -> Optional[PageRequest]:
        header = response.headers.get("Link") or response.headers.get("link")
        if not header:
            return None
        next_url = _parse_link_header(header).get("next")
        if not next_url:
            return None
        return PageRequest(url=next_url)


def _parse_link_header(header: str) -> Dict[str, str]:
    """Parse a ``Link`` header into a ``{rel: url}`` mapping."""
    links: Dict[str, str] = {}
    for part in header.split(","):
        segments = part.split(";")
        if len(segments) < 2:
            continue
        url = segments[0].strip().lstrip("<").rstrip(">")
        for segment in segments[1:]:
            key, _, value = segment.strip().partition("=")
            if key.strip() == "rel":
                links[value.strip().strip('"')] = url
    return links
