from typing import ClassVar

from fanfan.core.events.base import AppEvent
from fanfan.core.vo.user import UserId


class EmailConfirmationCodeRequested(AppEvent):
    subject: ClassVar[str] = "users.email_confirmation_code_requested"

    user_id: UserId


class EmailLoginCodeRequested(AppEvent):
    subject: ClassVar[str] = "users.email_login_code_requested"

    user_id: UserId
