from typing import ClassVar

from fanfan.application.commands.base import Command
from fanfan.core.models.notification import NewNotification
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole


class CreateNotificationCommand(Command):
    subject: ClassVar[str] = "cmd.notifications.create"

    notification: NewNotification


class ProcessBroadcastCommand(Command):
    subject: ClassVar[str] = "cmd.notifications.broadcast.process"

    mailing_id: MailingId
    body: str
    roles: list[UserRole]


class CancelMailingCommand(Command):
    subject: ClassVar[str] = "cmd.notifications.mailing.cancel"

    mailing_id: MailingId
