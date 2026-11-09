"""Parameter markers used inside ``Annotated[...]`` to route arguments."""

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Optional


class Location(str, Enum):
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"
    FORM = "form"
    FILE = "file"


@dataclass(frozen=True)
class Param:
    location: ClassVar[Location]
    alias: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class Path(Param):
    location: ClassVar[Location] = Location.PATH
    alias: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class Query(Param):
    location: ClassVar[Location] = Location.QUERY
    alias: Optional[str] = None


@dataclass(frozen=True)
class Header(Param):
    location: ClassVar[Location] = Location.HEADER


@dataclass(frozen=True, kw_only=True)
class Cookie(Param):
    location: ClassVar[Location] = Location.COOKIE
    alias: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class Form(Param):
    location: ClassVar[Location] = Location.FORM
    alias: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class File(Param):
    location: ClassVar[Location] = Location.FILE
    alias: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class Body(Param):
    location: ClassVar[Location] = Location.BODY
    alias: Optional[str] = field(default=None, init=False)
    exclude_unset: bool = False
    exclude_none: bool = False
