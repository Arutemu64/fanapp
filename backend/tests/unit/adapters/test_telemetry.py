import pytest

from fanfan.adapters.debug.telemetry import (
    _is_asyncpg_teardown_timeout,
    _scrub_sensitive_data,
)
from fanfan.core.exceptions.base import AppException

pytestmark = pytest.mark.unit


def _raise_from(module_name: str, func_name: str) -> TimeoutError:
    """Return a TimeoutError whose traceback runs through ``func_name`` in a
    frame whose module is ``module_name`` — the two attributes the teardown
    filter matches on. Building the frame this way avoids importing the real
    asyncpg dialect (which would try to open a connection)."""
    namespace: dict = {"__name__": module_name}
    exec(f"def {func_name}():\n    raise TimeoutError()\n", namespace)  # noqa: S102
    try:
        namespace[func_name]()
    except TimeoutError as exc:
        return exc
    msg = "expected TimeoutError"
    raise AssertionError(msg)  # pragma: no cover


def test_recognises_asyncpg_teardown_timeout() -> None:
    exc = _raise_from(
        "sqlalchemy.dialects.postgresql.asyncpg", "_terminate_graceful_close"
    )
    assert _is_asyncpg_teardown_timeout(exc) is True


def test_ignores_unrelated_timeout() -> None:
    # Same exception type, but not the graceful-close teardown path.
    exc = _raise_from("fanfan.adapters.some_client", "fetch")
    assert _is_asyncpg_teardown_timeout(exc) is False


def test_ignores_timeout_from_a_different_close() -> None:
    # Right function name, wrong module: not SQLAlchemy's teardown.
    exc = _raise_from("some.other.module", "_terminate_graceful_close")
    assert _is_asyncpg_teardown_timeout(exc) is False


def test_before_send_drops_teardown_timeout() -> None:
    exc = _raise_from(
        "sqlalchemy.dialects.postgresql.asyncpg", "_terminate_graceful_close"
    )
    hint = {"exc_info": (type(exc), exc, exc.__traceback__)}
    assert _scrub_sensitive_data({}, hint) is None


def test_before_send_keeps_unrelated_timeout() -> None:
    exc = _raise_from("fanfan.adapters.some_client", "fetch")
    event: dict = {"request": {"headers": {}}}
    hint = {"exc_info": (type(exc), exc, exc.__traceback__)}
    assert _scrub_sensitive_data(event, hint) is event


def test_before_send_still_drops_app_exception() -> None:
    exc = AppException()
    hint = {"exc_info": (type(exc), exc, exc.__traceback__)}
    assert _scrub_sensitive_data({}, hint) is None


def test_before_send_filters_sensitive_headers() -> None:
    event = {
        "request": {
            "headers": {
                "Cookie": "session=secret",
                "Authorization": "Bearer token",
                "Accept": "*/*",
            }
        }
    }
    result = _scrub_sensitive_data(event, {})
    assert result is not None
    headers = result["request"]["headers"]
    assert headers["Cookie"] == "[Filtered]"
    assert headers["Authorization"] == "[Filtered]"
    assert headers["Accept"] == "*/*"
