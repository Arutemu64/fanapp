import importlib
import pkgutil

import pytest

import fanfan.application.commands
import fanfan.core.events
from fanfan.application.commands.base import Command
from fanfan.core.events.base import Message
from fanfan.presentation.worker.app import routes

pytestmark = pytest.mark.unit


def _all_message_types() -> list[type[Message]]:
    # Import every events and commands module first: a subclass is only
    # registered once its module has been imported, and nothing else guarantees
    # that here.
    for package in (fanfan.core.events, fanfan.application.commands):
        for module in pkgutil.iter_modules(package.__path__):
            importlib.import_module(f"{package.__name__}.{module.name}")
    found: list[type[Message]] = []
    pending = list(Message.__subclasses__())
    while pending:
        message_type = pending.pop()
        pending.extend(message_type.__subclasses__())
        # The bases carry no subject, and tests define throwaway subclasses;
        # only the app's own concrete messages count.
        if "subject" not in vars(message_type):
            continue
        if message_type.__module__.startswith("fanfan."):
            found.append(message_type)
    return found


def test_every_message_has_a_subscriber() -> None:
    # The UnitOfWork queues one job per task subscribed to a message's subject
    # and refuses a message with none (UnroutedMessageError), which would fail
    # the commit that produced it. Catch that here rather than in production.
    orphaned = [
        f"{message_type.__name__} ({message_type.subject})"
        for message_type in _all_message_types()
        if not routes.get(message_type.subject)
    ]

    assert orphaned == [], f"Messages with no subscriber: {orphaned}"


def test_every_command_has_exactly_one_handler() -> None:
    # A command is a work order (ADR-0040): a second subscriber would do the
    # work twice.
    shared = [
        message_type.__name__
        for message_type in _all_message_types()
        if issubclass(message_type, Command)
        and len(routes.get(message_type.subject, ())) > 1
    ]

    assert shared == [], f"Commands with several handlers: {shared}"
