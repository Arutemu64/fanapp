import asyncio
from typing import Any, cast

import pytest
from faststream.nats import NatsBroker

from fanfan.adapters.nats import events_broker
from fanfan.adapters.nats.events_broker import NatsEventBroker
from fanfan.core.events.notifications import NotificationCreated
from fanfan.core.vo.notification import NotificationId, generate_notification_id

pytestmark = pytest.mark.asyncio


class PublishRejected(Exception):
    pass


class StubNatsBroker:
    """Records publishes, fails chosen events and tracks peak concurrency."""

    def __init__(
        self,
        failing: set[NotificationId] | None = None,
        cancelled: set[NotificationId] | None = None,
    ) -> None:
        self.failing = failing or set()
        self.cancelled = cancelled or set()
        self.published: list[NotificationId] = []
        self.in_flight = 0
        self.peak_in_flight = 0

    async def publish(self, message: NotificationCreated, **_: Any) -> None:
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        try:
            # Yield so concurrent publishes actually overlap.
            await asyncio.sleep(0)
            if message.notification_id in self.failing:
                raise PublishRejected
            if message.notification_id in self.cancelled:
                raise asyncio.CancelledError
            self.published.append(message.notification_id)
        finally:
            self.in_flight -= 1


def _events(count: int) -> list[NotificationCreated]:
    return [
        NotificationCreated(notification_id=generate_notification_id())
        for _ in range(count)
    ]


async def test_one_failed_publish_does_not_stop_the_others() -> None:
    events = _events(5)
    rejected = events[1].notification_id
    stub = StubNatsBroker(failing={rejected})

    with pytest.raises(ExceptionGroup) as error:
        await NatsEventBroker(cast("NatsBroker", stub)).publish_many(events)

    assert error.value.subgroup(PublishRejected) is not None
    assert len(error.value.exceptions) == 1
    assert sorted(stub.published) == sorted(
        event.notification_id for event in events if event.notification_id != rejected
    )


async def test_in_flight_publishes_stay_under_the_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(events_broker, "_MAX_IN_FLIGHT_PUBLISHES", 3)
    stub = StubNatsBroker()

    await NatsEventBroker(cast("NatsBroker", stub)).publish_many(_events(20))

    assert len(stub.published) == 20
    assert stub.peak_in_flight == 3


async def test_a_publish_cancelled_on_its_own_counts_as_failed() -> None:
    # The fan-out task itself is not cancelled, so gather hands the child's
    # CancelledError back as a result; dropping it would ack a lost event.
    events = _events(3)
    stub = StubNatsBroker(cancelled={events[0].notification_id})

    with pytest.raises(ExceptionGroup) as error:
        await NatsEventBroker(cast("NatsBroker", stub)).publish_many(events)

    assert len(error.value.exceptions) == 1
    assert isinstance(error.value.exceptions[0].__cause__, asyncio.CancelledError)
    assert len(stub.published) == 2
