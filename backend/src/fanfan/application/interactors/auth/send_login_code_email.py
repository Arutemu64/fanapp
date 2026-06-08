from pydantic import BaseModel

from fanfan.adapters.jinja.factory import JinjaEnvironment
from fanfan.application.ports.email_sender import (
    EmailMessage,
    EmailRecipient,
    EmailSender,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_login import (
    EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    generate_numeric_code,
)
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserId


class SendLoginCodeEmailInput(BaseModel):
    user_id: UserId


class SendLoginCodeEmail:
    def __init__(
        self,
        user_repo: UserRepository,
        email_sender: EmailSender,
        jinja: JinjaEnvironment,
        token_registry: TokenRegistry,
    ):
        self.email_sender = email_sender
        self.jinja = jinja
        self.user_repo = user_repo
        self.token_registry = token_registry

    async def __call__(self, data: SendLoginCodeEmailInput) -> None:
        user = await self.user_repo.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        if user.email is None:
            raise UserHasNoEmail
        normalized_email = normalize_email(user.email)

        code = generate_numeric_code()
        await self.token_registry.issue_email_login_code(
            user_id=user.id,
            email=normalized_email,
            code=code,
            ttl_seconds=EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
        )

        template = self.jinja.get_template("email_login_code.jinja2")
        message_body = await template.render_async(
            {
                "username": user.username,
                "login_code": code,
                "expires_in_minutes": max(1, EMAIL_LOGIN_CODE_MAX_AGE_SECONDS // 60),
            }
        )
        message = EmailMessage(
            subject="Код входа в FAN FAN",
            recipients=[
                EmailRecipient(name=user.username or "", email=normalized_email)
            ],
            html_body=message_body,
        )
        await self.email_sender.send(message)
