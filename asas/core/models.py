from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union


@dataclass
class Payload:
    """A general container for request data."""

    data: Optional[Any] = None
    json: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class Request:
    """Protocol-agnostic request model."""

    method: str
    url: str
    params: Optional[Dict[str, Any]] = None
    headers: Dict[str, str] = field(default_factory=dict)
    payload: Optional[Payload] = None
    timeout: Optional[float] = None


@dataclass
class Response:
    """Protocol-agnostic response model."""

    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str

    def json(self) -> Any:
        import json

        return json.loads(self.content)
