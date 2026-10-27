import logging
from datetime import datetime
from typing import Any, ClassVar
from uuid import uuid7

import pytest
import sentry_sdk
from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import OutboxEventORM
from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.application.interactors.outbox.publish_outbox_events import (
    _STUCK_AFTER_ATTEMPTS,
    PublishOutboxEvents,
)
from fanfan.application.interactors.outbox.publish_outbox_events import (
    logger as relay_logger,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import DomainEvent
from fanfan.core.models.base import AggregateRoot
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
        self,
        subject: str,
        payload: dict[str, Any],
        message_id: str,
        occurred_at: datetime,
        trace_headers: dict[str, str] | None,
    ) -> None:
        if subject == self.fail_subject:
            msg = "NATS rejected the publish"
            raise ConnectionError(msg)
        await super().publish_raw(
            subject, payload, message_id, occurred_at, trace_headers
        )


async def make_relay(
    dishka_request: AsyncContainer, events_broker: EventBroker
) -> PublishOutboxEvents:
    return PublishOutboxEvents(
        outbox_gateway=await dishka_request.get(OutboxGateway),
        events_broker=events_broker,
        uow=await dishka_request.get(UnitOfWork),
        config=OutboxConfig(),
    )


async def test_relay_publishes_pending_events_in_creation_order(
    dishka_request: AsyncContainer,
    outbox: OutboxGateway,
) -> None:
    session = await dishka_request.get(AsyncSession)
    first = OutboxEventORM(id=uuid7(), subject="test.event", payload={"n": 1})
    second = OutboxEventORM(id=uuid7(), subject="test.event", payload={"n": 2})
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
    await session.refresh(first)
    assert events_broker.published_occurred_at == [first.created_at] * 2
    assert await outbox.fetch_unpublished(10) == []


async def test_relay_drains_a_backlog_larger_than_one_batch(
    dishka_request: AsyncContainer,
    outbox: OutboxGateway,
) -> None:
    session = await dishka_request.get(AsyncSession)
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
) -> None:
    session = await dishka_request.get(AsyncSession)
    delivered = OutboxEventORM(id=uuid7(), subject="test.ok", payload={"n": 1})
    poisoned = OutboxEventORM(id=uuid7(), subject="test.bad", payload={"n": 2})
    session.add(delivered)
    session.add(poisoned)
    await session.flush()

    events_broker = FailingEventBroker(fail_subject="test.bad")
    relay = await make_relay(dishka_request, events_broker)
    await relay()

    assert events_broker.published_raw == [("test.ok", {"n": 1}, str(delivered.id))]
    await session.refresh(poisoned)
    assert poisoned.published_at is None
    assert poisoned.attempts == 1
    assert poisoned.last_error == "ConnectionError: NATS rejected the publish"
    assert poisoned.next_attempt_at is not None
    assert await outbox.fetch_unpublished(10) == []


async def test_failed_row_does_not_block_the_rows_behind_it(
    dishka_request: AsyncContainer,
    outbox: OutboxGateway,
) -> None:
    session = await dishka_request.get(AsyncSession)
    poisoned = OutboxEventORM(id=uuid7(), subject="test.bad", payload={"n": 1})
    behind = OutboxEventORM(id=uuid7(), subject="test.ok", payload={"n": 2})
    session.add(poisoned)
    session.add(behind)
    await session.flush()

    events_broker = FailingEventBroker(fail_subject="test.bad")
    relay = await make_relay(dishka_request, events_broker)
    await relay()
    assert events_broker.published_raw == []
    await relay()

    assert events_broker.published_raw == [("test.ok", {"n": 2}, str(behind.id))]
    assert await outbox.fetch_unpublished(10) == []


async def test_relay_reports_a_row_stuck_after_repeated_failures(
    dishka_request: AsyncContainer,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = await dishka_request.get(AsyncSession)
    poisoned = OutboxEventORM(
        id=uuid7(), subject="test.bad", payload={}, attempts=_STUCK_AFTER_ATTEMPTS - 1
    )
    session.add(poisoned)
    await session.flush()

    relay = await make_relay(
        dishka_request, FailingEventBroker(fail_subject="test.bad")
    )
    monkeypatch.setattr(relay_logger, "disabled", False)
    with caplog.at_level(logging.WARNING):
        await relay()

    [record] = [r for r in caplog.records if r.name == relay_logger.name]
    assert record.levelno == logging.ERROR
    assert record.__dict__["relay_event"] == "publish_stuck"
    assert record.__dict__["attempt"] == _STUCK_AFTER_ATTEMPTS


class _TracedEvent(DomainEvent):
    subject: ClassVar[str] = "test.traced"


@pytest.mark.usefixtures("tracing")
async def test_relay_forwards_the_trace_of_the_request_that_wrote_the_event(
    dishka_request: AsyncContainer,
) -> None:
    uow = await dishka_request.get(UnitOfWork)
    aggregate = AggregateRoot()
    aggregate.record_event(_TracedEvent())
    with sentry_sdk.start_transaction(name="POST /request") as transaction:
        uow.register(aggregate)
        await uow.commit()

    events_broker = FakeEventBroker()
    relay = await make_relay(dishka_request, events_broker)
    await relay()

    [trace_headers] = events_broker.published_trace_headers
    assert trace_headers is not None
    assert trace_headers["sentry-trace"].startswith(transaction.trace_id)
