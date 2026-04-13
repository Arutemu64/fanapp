from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, NameEmail

from fanfan.adapters.jinja.factory import StreamJinjaEnvironment
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_login import (
    EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    EmailService,
)
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserId


class SendLoginCodeEmailInput(BaseModel):
    user_id: UserId


class SendLoginCodeEmail:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
        mail: FastMail,
        jinja: StreamJinjaEnvironment,
        token_registry: TokenRegistry,
    ):
        self.mail = mail
        self.jinja = jinja
        self.user_repo = user_repo
        self.email_service = email_service
        self.token_registry = token_registry

    async def __call__(self, data: SendLoginCodeEmailInput) -> None:
        user = await self.user_repo.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        if user.email is None:
            raise UserHasNoEmail
        normalized_email = normalize_email(user.email)

        code = self.email_service.generate_login_code(user_id=user.id)
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
        message = MessageSchema(
            subject="Код входа в FAN FAN",
            recipients=[NameEmail(name=user.username, email=normalized_email)],
            body=message_body,
            # Send HTML so the email client renders the code block cleanly.
            subtype=MessageType.html,
        )
        await self.mail.send_message(message)