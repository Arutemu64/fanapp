import importlib
import pkgutil

import pytest
from faststream.nats import NatsBroker
from faststream.nats.subscriber import LogicSubscriber

import fanfan.application.commands
import fanfan.core.events
from fanfan.core.events.base import Message
from fanfan.presentation.faststream.jstream import stream
from fanfan.presentation.faststream.routes import setup_router

pytestmark = pytest.mark.unit


def _all_message_types() -> list[type[Message]]:
    for package in (fanfan.core.events, fanfan.application.commands):
        for module in pkgutil.iter_modules(package.__path__):
            importlib.import_module(f"{package.__name__}.{module.name}")
    found: list[type[Message]] = []
    pending = list(Message.__subclasses__())
    while pending:
        message_type = pending.pop()
        pending.extend(message_type.__subclasses__())
        if "subject" not in vars(message_type):
            continue
        if message_type.__module__.startswith("fanfan."):
            found.append(message_type)
    return found


def _stream_subscriber_subjects() -> list[str]:
    broker = NatsBroker()
    broker.include_router(setup_router())
    subjects: list[str] = []
    for subscriber in broker.subscribers:
        assert isinstance(subscriber, LogicSubscriber)
        subscriber_stream = getattr(subscriber, "stream", None)
        if subscriber_stream is None or subscriber_stream.name != stream.name:
            continue
        subjects.append(subscriber.subject.template)
    return subjects


def _subject_matches(pattern: str, subject: str) -> bool:
    pattern_tokens = pattern.split(".")
    subject_tokens = subject.split(".")
    for index, token in enumerate(pattern_tokens):
        if token == ">":
            return len(subject_tokens) > index
        if index >= len(subject_tokens):
            return False
        if token not in {"*", subject_tokens[index]}:
            return False
    return len(pattern_tokens) == len(subject_tokens)


def test_every_message_has_a_stream_subscriber() -> None:
    subscribed = _stream_subscriber_subjects()
    orphaned = [
        f"{message_type.__name__} ({message_type.subject})"
        for message_type in _all_message_types()
        if not any(_subject_matches(p, message_type.subject) for p in subscribed)
    ]

    assert orphaned == [], f"Messages with no stream subscriber: {orphaned}"


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
