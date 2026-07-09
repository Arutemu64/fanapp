from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EmailRecipient:
    name: str
    email: str


@dataclass(frozen=True, slots=True)
class EmailMessage:
    subject: str
    recipients: list[EmailRecipient]
    html_body: str
    # Optional plain-text alternative. Sending multipart/alternative improves
    # deliverability (spam scoring) and degrades gracefully in text-only clients.
    text_body: str | None = None


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...
