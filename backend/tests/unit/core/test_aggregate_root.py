import pytest

from fanfan.core.events.base import AppEvent
from fanfan.core.models.base import AggregateRoot

pytestmark = pytest.mark.unit


class _DummyEvent(AppEvent):
    subject = "tests.dummy"

    value: int


def test_record_event_accumulates_events_in_order():
    aggregate = AggregateRoot()

    first = _DummyEvent(value=1)
    second = _DummyEvent(value=2)
    aggregate.record_event(first)
    aggregate.record_event(second)

    assert aggregate.pull_events() == [first, second]


def test_pull_events_clears_the_buffer():
    aggregate = AggregateRoot()
    aggregate.record_event(_DummyEvent(value=1))

    aggregate.pull_events()

    assert aggregate.pull_events() == []
