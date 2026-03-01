from typing import ClassVar

from fanfan.core.events.base import AppEvent
from fanfan.core.vo.user import UserId


class CreatedUserEvent(AppEvent):
    subject: ClassVar[str] = "users.created"

    user_id: UserId


class EmailVerificationRequestedEvent(AppEvent):
    subject: ClassVar[str] = "users.email_verification_requested"

    user_id: UserId
