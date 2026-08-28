"""Conditions that decide *when* a refreshable auth should refresh.

By default an auth refreshes only on an HTTP ``401``. Real APIs disagree: some
return ``200`` with an error code in the body, some put a keyword in the
payload, some use a non-standard status. A :data:`RefreshCondition` is just a
``Callable[[Response], bool]`` — pass one as ``refresh_when=`` to a refreshable
auth, compose the ready-made builders below, or override ``should_refresh`` on a
subclass for full control.
"""

from typing import Any, Callable, Optional

from asas.core.models import Response

#: A predicate over a response: return ``True`` when the auth should refresh.
RefreshCondition = Callable[[Response], bool]

_UNSET: Any = object()
_MISSING: Any = object()


def _dig(data: Any, dotted_key: str) -> Any:
    """Look up a nested key like ``"error.code"``; return ``_MISSING`` if absent."""
    current = data
    for part in dotted_key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def refresh_on_status(*status_codes: int) -> RefreshCondition:
    """Refresh when the response status is one of ``status_codes`` (default 401)."""
    codes = set(status_codes) or {401}

    def condition(response: Response) -> bool:
        return response.status_code in codes

    return condition


def refresh_on_keyword(keyword: str, *, ignore_case: bool = True) -> RefreshCondition:
    """Refresh when ``keyword`` appears anywhere in the response body text."""
    needle = keyword.lower() if ignore_case else keyword

    def condition(response: Response) -> bool:
        text = response.text.lower() if ignore_case else response.text
        return needle in text

    return condition


def refresh_on_json(
    key: str, value: Any = _UNSET, *, status: Optional[int] = None
) -> RefreshCondition:
    """Refresh based on the JSON body.

    ``key`` may be a dotted path (``"error.code"``). With no ``value``, the
    condition is true when the key is present; with a ``value`` it must also be
    equal. Pass ``status`` to additionally require a specific status code (e.g.
    a ``200`` response whose body signals an expired token).
    """

    def condition(response: Response) -> bool:
        if status is not None and response.status_code != status:
            return False
        try:
            data = response.json()
        except Exception:
            return False
        found = _dig(data, key)
        if found is _MISSING:
            return False
        return True if value is _UNSET else bool(found == value)

    return condition


def refresh_on_any(*conditions: RefreshCondition) -> RefreshCondition:
    """Refresh when *any* of the given conditions is true."""

    def condition(response: Response) -> bool:
        return any(check(response) for check in conditions)

    return condition


def refresh_on_all(*conditions: RefreshCondition) -> RefreshCondition:
    """Refresh only when *all* of the given conditions are true."""

    def condition(response: Response) -> bool:
        return all(check(response) for check in conditions)

    return condition


def evaluate_refresh(auth: Any, response: Response) -> bool:
    """Return whether ``auth`` wants to refresh for ``response``.

    Uses the auth's ``should_refresh`` method when it has one, otherwise falls
    back to the default behaviour (refresh on HTTP ``401``). This keeps auth
    strategies that only implement ``refresh``/``arefresh`` working unchanged.
    """
    checker = getattr(auth, "should_refresh", None)
    if callable(checker):
        return bool(checker(response))
    return response.status_code == 401
