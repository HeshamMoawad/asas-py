from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Payload:
    """A general container for request data."""

    data: dict[str, Any] | bytes | None = None
    json: Any = None
    files: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Request:
    """Protocol-agnostic request model."""

    method: str
    url: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    payload: Payload | None = None
    timeout: float | None = None


@dataclass
class Response:
    """Protocol-agnostic response model."""

    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str

    def json(self) -> Any:
        import json

        return json.loads(self.content)
