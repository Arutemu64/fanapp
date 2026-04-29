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


class EmailSender(Protocol):
    async def send(self, message: EmailMessage) -> None: ...
