from types import SimpleNamespace
from typing import Any, cast

import pytest
import sentry_sdk
from nats.aio.msg import Msg

from fanfan.adapters.debug.tracing import current_trace_headers
from fanfan.presentation.faststream.middleware import SentryMiddleware

pytestmark = pytest.mark.unit

_TRACE_ID = "771a43a4192642f0b136d5159a501700"
_PARENT = f"{_TRACE_ID}-b0e6f15b45c36b12-1"


def _middleware() -> SentryMiddleware:
    # The middleware never reads its FastStream context.
    return SentryMiddleware(None, context=cast("Any", None))


def _message(headers: dict[str, str]) -> Any:  # noqa: ANN401  # stand-in StreamMessage
    raw = Msg(_client=cast("Any", None), subject="probe", data=b"{}")
    return SimpleNamespace(headers=headers, raw_message=raw, message_id="m-1")


def _command(headers: dict[str, str]) -> Any:  # noqa: ANN401  # stand-in PublishCommand
    return SimpleNamespace(destination="probe", headers=headers)


@pytest.mark.asyncio
@pytest.mark.usefixtures("tracing")
async def test_consumer_continues_the_producer_trace() -> None:
    seen: list[str] = []

    async def handler(_msg: object) -> None:
        seen.append(sentry_sdk.get_traceparent() or "")

    await _middleware().consume_scope(handler, _message({"sentry-trace": _PARENT}))

    [traceparent] = seen
    assert traceparent.startswith(_TRACE_ID)


@pytest.mark.asyncio
@pytest.mark.usefixtures("tracing")
async def test_publish_inside_a_trace_stamps_its_headers() -> None:
    cmd = _command({})

    async def send(_cmd: object) -> None: ...

    with sentry_sdk.start_transaction(name="request") as transaction:
        await _middleware().publish_scope(send, cmd)

    assert cmd.headers["sentry-trace"].startswith(transaction.trace_id)


@pytest.mark.asyncio
@pytest.mark.usefixtures("tracing")
async def test_publish_keeps_trace_headers_the_relay_forwarded() -> None:
    # The relay publishes the writer's stored trace; the relay's own context
    # must not overwrite it.
    cmd = _command({"sentry-trace": _PARENT})

    async def send(_cmd: object) -> None: ...

    with sentry_sdk.start_transaction(name="relay"):
        await _middleware().publish_scope(send, cmd)

    assert cmd.headers["sentry-trace"] == _PARENT


@pytest.mark.usefixtures("tracing")
def test_no_trace_headers_outside_a_span() -> None:
    # Outside a span the scope still has a fallback trace id; stamping it would
    # join every message the scheduler sends into one endless trace.
    assert current_trace_headers() == {}
