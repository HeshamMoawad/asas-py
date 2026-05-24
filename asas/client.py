from typing import Any, Optional

from asas.core.engine import Engine
from asas.decorators import delete, get, patch, post, put
from asas.engines.httpx import HTTPXEngine


class AsasClient:
    """
    Base client for building API clients.
    """

    def __init__(
        self, base_url: str = "", engine: Optional[Engine] = None, **kwargs: Any
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.engine = engine or HTTPXEngine(**kwargs)
