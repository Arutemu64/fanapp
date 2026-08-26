from typing import Any
from uuid import uuid7

import pytest
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import OutboxEventORM
from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.application.interactors.outbox.publish_outbox_events import (
    PublishOutboxEvents,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork
from tests.fakes.event_broker import FakeEventBroker

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


class FailingEventBroker(FakeEventBroker):
    """Fails one subject to simulate a mid-batch NATS publish error."""

    def __init__(self, fail_subject: str) -> None:
        super().__init__()
        self.fail_subject = fail_subject

    async def publish_raw(
        self, subject: str, payload: dict[str, Any], message_id: str
    ) -> None:
        if subject == self.fail_subject:
            msg = "NATS rejected the publish"
            raise ConnectionError(msg)
        await super().publish_raw(subject, payload, message_id)


async def make_relay(
    dishka_request: AsyncContainer, events_broker: EventBroker
) -> PublishOutboxEvents:
    # The test container carries no EnvConfig, so wire the relay by hand
    # with default tuning instead of resolving it from DI.
    return PublishOutboxEvents(
        outbox_gateway=await dishka_request.get(OutboxGateway),
        events_broker=events_broker,
        uow=await dishka_request.get(UnitOfWork),
        config=OutboxConfig(),
    )


async def test_relay_publishes_pending_events_in_creation_order(
    dishka_request: AsyncContainer,
    outbox: OutboxGateway,
):
    session = await dishka_request.get(AsyncSession)
    first = OutboxEventORM(id=uuid7(), subject="test.event", payload={"n": 1})
    second = OutboxEventORM(id=uuid7(), subject="test.event", payload={"n": 2})
    # Rows from one transaction share created_at (it is the transaction
    # timestamp), so add them in reverse to prove the uuid7 id tiebreaker
    # restores creation order.
    session.add(second)
    session.add(first)
    await session.flush()

    events_broker = FakeEventBroker()
    relay = await make_relay(dishka_request, events_broker)
    await relay()

    assert events_broker.published_raw == [
        ("test.event", {"n": 1}, str(first.id)),
        ("test.event", {"n": 2}, str(second.id)),
    ]
    assert await outbox.fetch_unpublished(10) == []


async def test_relay_drains_a_backlog_larger_than_one_batch(
    dishka_request: AsyncContainer,
    outbox: OutboxGateway,
):
    session = await dishka_request.get(AsyncSession)
    # Three rows against a batch size of two: a single wake must drain all of
    # them, not stop after the first batch and leave the rest for the next tick.
    rows = [
        OutboxEventORM(id=uuid7(), subject="test.event", payload={"n": n})
        for n in range(3)
    ]
    for row in rows:
        session.add(row)
    await session.flush()

    events_broker = FakeEventBroker()
    relay = PublishOutboxEvents(
        outbox_gateway=await dishka_request.get(OutboxGateway),
        events_broker=events_broker,
        uow=await dishka_request.get(UnitOfWork),
        config=OutboxConfig(batch_size=2),
    )
    await relay()

    assert [payload["n"] for _, payload, _ in events_broker.published_raw] == [0, 1, 2]
    assert await outbox.fetch_unpublished(10) == []


async def test_relay_marks_delivered_prefix_when_a_publish_fails(
    dishka_request: AsyncContainer,
    outbox: OutboxGateway,
):
    session = await dishka_request.get(AsyncSession)
    delivered = OutboxEventORM(id=uuid7(), subject="test.ok", payload={"n": 1})
    poisoned = OutboxEventORM(id=uuid7(), subject="test.bad", payload={"n": 2})
    session.add(delivered)
    session.add(poisoned)
    await session.flush()

    events_broker = FailingEventBroker(fail_subject="test.bad")
    relay = await make_relay(dishka_request, events_broker)
    with pytest.raises(ConnectionError):
        await relay()

    # The row NATS acked before the failure must be marked published, so the
    # next tick retries only the failed row instead of republishing both.
    assert events_broker.published_raw == [("test.ok", {"n": 1}, str(delivered.id))]
    remaining = await outbox.fetch_unpublished(10)
    assert [m.id for m in remaining] == [poisoned.id]
