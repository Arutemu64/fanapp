from typing import ClassVar

from pydantic import BaseModel


class Message(BaseModel):
    """Anything queued as background work: a domain event or a command (ADR-0040).

    ``subject`` is the routing key: every task subscribed to it gets one job per
    message (ADR-0041).
    """

    subject: ClassVar[str]


class DomainEvent(Message):
    """A fact an aggregate records: past tense, any number of subscribers.

    Commands live in ``application/commands/`` — the instruction to do work
    belongs to the use case that asks for it, not to the domain.
    """
