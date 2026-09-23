import importlib
import pkgutil

import pytest
from faststream.nats import NatsBroker
from faststream.nats.subscriber import LogicSubscriber

import fanfan.core.events
from fanfan.core.events.base import AppEvent
from fanfan.presentation.faststream.jstream import stream
from fanfan.presentation.faststream.routes import setup_router

pytestmark = pytest.mark.unit


def _all_event_types() -> list[type[AppEvent]]:
    # Import every events module first: a subclass is only registered once its
    # module has been imported, and nothing else guarantees that here.
    for module in pkgutil.iter_modules(fanfan.core.events.__path__):
        importlib.import_module(f"{fanfan.core.events.__name__}.{module.name}")
    found: list[type[AppEvent]] = []
    pending = list(AppEvent.__subclasses__())
    while pending:
        event_type = pending.pop()
        pending.extend(event_type.__subclasses__())
        # Tests define throwaway AppEvent subclasses; only the app's own count.
        if event_type.__module__.startswith("fanfan."):
            found.append(event_type)
    return found


def _stream_subscriber_subjects() -> list[str]:
    broker = NatsBroker()
    broker.include_router(setup_router())
    subjects: list[str] = []
    for subscriber in broker.subscribers:
        assert isinstance(subscriber, LogicSubscriber)
        # Only JetStream subscribers carry a stream; a core one adds no subject.
        subscriber_stream = getattr(subscriber, "stream", None)
        if subscriber_stream is None or subscriber_stream.name != stream.name:
            continue
        subjects.append(subscriber.subject.template)
    return subjects


def _subject_matches(pattern: str, subject: str) -> bool:
    # NATS wildcards: `*` matches exactly one token, `>` one or more trailing ones.
    pattern_tokens = pattern.split(".")
    subject_tokens = subject.split(".")
    for index, token in enumerate(pattern_tokens):
        if token == ">":
            return len(subject_tokens) > index
        if index >= len(subject_tokens):
            return False
        if token not in ("*", subject_tokens[index]):
            return False
    return len(pattern_tokens) == len(subject_tokens)


def test_every_event_has_a_stream_subscriber() -> None:
    # FastStream adds a subject to the JetStream stream only when a subscriber on
    # that stream registers it; the stream itself declares just the SSE subjects.
    # An event nobody subscribes to therefore has no stream to land on: every
    # publish fails with "no response from stream", and the outbox relay retries
    # its rows forever. Catch that here rather than as a stuck-event alert.
    subscribed = _stream_subscriber_subjects()
    orphaned = [
        f"{event_type.__name__} ({event_type.subject})"
        for event_type in _all_event_types()
        if not any(_subject_matches(p, event_type.subject) for p in subscribed)
    ]

    assert orphaned == [], f"Events with no stream subscriber: {orphaned}"


@pytest.mark.parametrize(
    ("pattern", "subject", "expected"),
    [
        ("votes.created", "votes.created", True),
        ("votes.created", "votes.deleted", False),
        ("votes.*", "votes.created", True),
        ("votes.*", "votes.created.late", False),
        ("notifications.>", "notifications.broadcast.queued", True),
        ("notifications.>", "notifications", False),
        ("votes.created.late", "votes.created", False),
    ],
)
def test_subject_matches_follows_nats_wildcards(
    pattern: str, subject: str, *, expected: bool
) -> None:
    assert _subject_matches(pattern, subject) is expected
