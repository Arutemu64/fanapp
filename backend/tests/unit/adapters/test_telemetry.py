import asyncio
import inspect

import uvicorn.server
from sentry_sdk.types import Event

from fanfan.adapters.debug.telemetry import (
    UVICORN_SHUTDOWN_CANCEL_MESSAGE,
    UVICORN_SHUTDOWN_TIMEOUT_LOG,
    _drop_expected_errors,
)


def _never_expected(_: BaseException) -> bool:
    return False


def _chained_shutdown_cancel() -> asyncio.CancelledError:
    # Mirrors what uvicorn reports: a bare CancelledError whose context is the
    # one carrying uvicorn's message.
    outer = asyncio.CancelledError()
    outer.__context__ = asyncio.CancelledError(UVICORN_SHUTDOWN_CANCEL_MESSAGE)
    return outer


def test_shutdown_strings_match_installed_uvicorn() -> None:
    source = inspect.getsource(uvicorn.server)
    assert UVICORN_SHUTDOWN_TIMEOUT_LOG in source
    assert UVICORN_SHUTDOWN_CANCEL_MESSAGE in source


def test_drops_uvicorn_shutdown_timeout_log() -> None:
    event: Event = {
        "logger": "uvicorn.error",
        "logentry": {"message": UVICORN_SHUTDOWN_TIMEOUT_LOG},
    }
    assert _drop_expected_errors(event, {}, _never_expected) is None


def test_drops_request_cancelled_by_shutdown_timeout() -> None:
    exc = _chained_shutdown_cancel()
    hint = {"exc_info": (type(exc), exc, None)}
    assert _drop_expected_errors({}, hint, _never_expected) is None


def test_keeps_other_cancellations_and_errors() -> None:
    for exc in (asyncio.CancelledError(), RuntimeError("boom")):
        hint = {"exc_info": (type(exc), exc, None)}
        assert _drop_expected_errors({}, hint, _never_expected) == {}


def test_keeps_cleanup_error_raised_during_shutdown_cancel() -> None:
    exc = RuntimeError("cleanup failed")
    exc.__context__ = asyncio.CancelledError(UVICORN_SHUTDOWN_CANCEL_MESSAGE)
    hint = {"exc_info": (type(exc), exc, None)}
    assert _drop_expected_errors({}, hint, _never_expected) == {}
