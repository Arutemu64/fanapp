import asyncio
from typing import Any, cast

import pytest
from faststream import AckPolicy
from faststream.exceptions import NackMessage
from faststream.nats import NatsBroker
from nats.aio.msg import Msg
from nats.js.api import ConsumerConfig

from fanfan.presentation.faststream.redelivery import (
    MAX_DELIVER,
    RedeliveryMiddleware,
    changed_consumer_fields,
    consumer_config,
    in_progress_heartbeat,
)
from fanfan.presentation.faststream.routes import setup_router

pytestmark = pytest.mark.unit


class _FakeClient:
    """Records the ack frames a Msg sends back to the server."""

    def __init__(self) -> None:
        self.sent: list[bytes] = []

    async def publish(self, _subject: str, payload: bytes = b"") -> None:
        self.sent.append(payload)


def _delivery(deliveries: int) -> tuple[Msg, _FakeClient]:
    client = _FakeClient()
    # JetStream v1 ack subject: stream, consumer, delivered, stream seq,
    # consumer seq, timestamp, pending.
    reply = f"$JS.ACK.stream.durable.{deliveries}.7.7.1695456000000000000.0"
    msg = Msg(_client=cast("Any", client), subject="probe", reply=reply)
    return msg, client


async def _fail(msg: Msg, error: BaseException) -> None:
    # The middleware never reads its FastStream context.
    middleware = RedeliveryMiddleware(msg, context=cast("Any", None))
    await middleware.after_processed(type(error), error, None)


@pytest.mark.asyncio
async def test_failure_is_redelivered_after_a_delay() -> None:
    msg, client = _delivery(deliveries=1)

    await _fail(msg, RuntimeError("boom"))

    # A delayed nak ("-NAK" plus a delay body), never the immediate plain nak
    # that would retry a transient failure in a hot loop.
    [frame] = client.sent
    assert frame.startswith(b"-NAK {")


@pytest.mark.asyncio
async def test_failure_on_the_last_delivery_is_terminated() -> None:
    msg, client = _delivery(deliveries=MAX_DELIVER)

    await _fail(msg, RuntimeError("boom"))

    assert client.sent == [b"+TERM"]


@pytest.mark.asyncio
async def test_message_the_handler_already_settled_is_left_alone() -> None:
    msg, client = _delivery(deliveries=1)
    await msg.ack()
    client.sent.clear()

    await _fail(msg, RuntimeError("boom"))

    assert client.sent == []


@pytest.mark.asyncio
async def test_faststream_ack_exceptions_are_left_to_the_ack_policy() -> None:
    msg, client = _delivery(deliveries=1)

    await _fail(msg, NackMessage())

    assert client.sent == []


def test_every_durable_consumer_is_bounded_and_redelivers() -> None:
    broker = NatsBroker()
    broker.include_router(setup_router())
    for subscriber in broker.subscribers:
        config = getattr(subscriber, "config", None)
        name = config.durable_name if config else subscriber
        # Unbounded MaxDeliver lets a poison message loop forever.
        assert config is not None
        assert config.max_deliver == MAX_DELIVER, name
        # FastStream's NATS default terminates a message on the first error,
        # losing the event; every consumer must redeliver or ack by hand.
        ack_policy = getattr(subscriber, "ack_policy", None)
        assert ack_policy is not AckPolicy.REJECT_ON_ERROR, name


class _ProgressRecorder:
    def __init__(self) -> None:
        self.beats = 0

    async def in_progress(self) -> None:
        self.beats += 1


@pytest.mark.asyncio
async def test_heartbeat_extends_ack_wait_until_the_handler_returns() -> None:
    msg = _ProgressRecorder()

    async with in_progress_heartbeat(cast("Any", msg), interval=0.01):
        await asyncio.sleep(0.05)
    beats_while_running = msg.beats
    await asyncio.sleep(0.03)

    assert beats_while_running >= 2
    # Stops with the handler: a finished message must not keep being extended.
    assert msg.beats == beats_while_running


def test_config_diff_names_only_the_declared_fields_that_differ() -> None:
    # The server fills in defaults the declaration leaves unset (None); those
    # must not read as changes, or every startup would log a spurious update.
    server = ConsumerConfig(
        durable_name="d", ack_wait=30.0, max_deliver=-1, max_ack_pending=1000
    )
    declared = consumer_config(ack_wait=90)
    declared.durable_name = "d"

    assert changed_consumer_fields(server, declared) == ["ack_wait", "max_deliver"]


def test_config_diff_is_empty_once_applied() -> None:
    declared = consumer_config(ack_wait=90)
    server = ConsumerConfig(
        ack_wait=90.0, max_deliver=MAX_DELIVER, max_ack_pending=1000
    )

    assert changed_consumer_fields(server, declared) == []
