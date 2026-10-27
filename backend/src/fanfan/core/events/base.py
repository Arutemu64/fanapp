from typing import ClassVar

from pydantic import BaseModel


class Message(BaseModel):
    """Anything published to NATS: a domain event or a command (ADR-0040)."""

    subject: ClassVar[str]

    def dedup_id(self) -> str | None:  # noqa: PLR6301
        """A stable id for this message, if it has one.

        A message republished with the same id — a redelivered trigger rerunning
        its fan-out — is dropped by the broker inside its dedup window. Messages
        without a natural identity return None and are never deduplicated.
        """
        return None


class DomainEvent(Message):
    """A fact an aggregate records: past tense, any number of subscribers.

    Commands live in ``application/commands/`` — the instruction to do work
    belongs to the use case that asks for it, not to the domain.
    """
