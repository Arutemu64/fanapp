from typing import ClassVar

from fanfan.application.commands.base import Command
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole


class CreateNotificationCommand(Command):
    subject: ClassVar[str] = "cmd.notifications.create"

    notification: NewNotification

    def dedup_id(self) -> str | None:
        # Unique per notification, and deterministic per recipient in the
        # fan-outs, so a rerun fan-out republishes the same id.
        return str(self.notification.id)


class ProcessBroadcastCommand(Command):
    subject: ClassVar[str] = "cmd.notifications.broadcast.process"

    mailing_id: MailingId
    body: str
    roles: list[UserRole]


class CancelMailingCommand(Command):
    subject: ClassVar[str] = "cmd.notifications.mailing.cancel"

    mailing_id: MailingId
