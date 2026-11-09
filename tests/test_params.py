import pytest

from asas.params import Body, Cookie, File, Form, Header, Location, Path, Query


def test_marker_locations() -> None:
    assert Path().location is Location.PATH and Query().location is Location.QUERY
    assert Header().location is Location.HEADER
    assert Cookie().location is Location.COOKIE
    assert Body().location is Location.BODY and Form().location is Location.FORM
    assert File().location is Location.FILE


def test_header_alias_positional_others_keyword_only() -> None:
    assert Header("X-Trace").alias == "X-Trace"
    assert Query(alias="pageSize").alias == "pageSize"
    with pytest.raises(TypeError):
        Query("pageSize")  # type: ignore[misc]


def test_body_options() -> None:
    b = Body(exclude_unset=True)
    assert b.exclude_unset and not b.exclude_none and b.alias is None


def test_markers_exported() -> None:
    import asas

    assert {"Path", "Query", "Header", "Cookie", "Body", "Form", "File"} <= set(
        asas.__all__
    )
