from typing import ClassVar

from fanfan.core.events.base import AppEvent
from fanfan.core.vo.user import UserId


class CreatedUserEvent(AppEvent):
    subject: ClassVar[str] = "users.created"

    user_id: UserId


class EmailConfirmationCodeRequestedEvent(AppEvent):
    subject: ClassVar[str] = "users.email_confirmation_code_requested"

    user_id: UserId


class EmailLoginCodeRequestedEvent(AppEvent):
    subject: ClassVar[str] = "users.email_login_code_requested"

    user_id: UserId
