from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, NameEmail

from fanfan.adapters.jinja.factory import JinjaEnvironment
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_login import (
    EMAIL_CONFIRMATION_CODE_MAX_AGE_SECONDS,
    EmailService,
)
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserId


class SendEmailConfirmationCodeInput(BaseModel):
    user_id: UserId


class SendEmailConfirmationCode:
    def __init__(
        self,
        user_repo: UserRepository,
        email_service: EmailService,
        mail: FastMail,
        jinja: JinjaEnvironment,
        token_registry: TokenRegistry,
    ):
        self.mail = mail
        self.jinja = jinja
        self.user_repo = user_repo
        self.email_service = email_service
        self.token_registry = token_registry

    async def __call__(self, data: SendEmailConfirmationCodeInput) -> None:
        user = await self.user_repo.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        target_email = user.pending_email or user.email
        if target_email is None:
            raise UserHasNoEmail
        target_email = normalize_email(target_email)

        code = self.email_service.generate_confirmation_code(user_id=user.id)
        await self.token_registry.issue_email_confirmation_code(
            user_id=user.id,
            email=target_email,
            code=code,
            ttl_seconds=EMAIL_CONFIRMATION_CODE_MAX_AGE_SECONDS,
        )

        template = self.jinja.get_template("email_confirmation_code.jinja2")
        message_body = await template.render_async(
            {
                "username": user.username,
                "confirmation_code": code,
                "expires_in_minutes": max(
                    1, EMAIL_CONFIRMATION_CODE_MAX_AGE_SECONDS // 60
                ),
            }
        )
        message = MessageSchema(
            subject="Подтвердите email в FAN FAN",
            recipients=[
                NameEmail(
                    name=user.username or "Пользователь",
                    email=target_email,
                )
            ],
            body=message_body,
            # Send HTML so the email client renders the code block cleanly.
            subtype=MessageType.html,
        )
        await self.mail.send_message(message)
