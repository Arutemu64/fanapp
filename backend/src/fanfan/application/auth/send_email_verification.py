from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, NameEmail

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.jinja.factory import StreamJinjaEnvironment
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_verification import (
    EMAIL_VERIFY_MAX_AGE_SECONDS,
    EmailVerificationService,
)
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class SendEmailVerificationCommand(BaseModel):
    user_id: UserId


class SendEmailVerification:
    def __init__(
        self,
        user_gateway: UserGateway,
        email_verification: EmailVerificationService,
        web_config: WebConfig,
        mail: FastMail,
        jinja: StreamJinjaEnvironment,
        token_registry: RedisAuthTokenRegistry,
    ):
        self.mail = mail
        self.jinja = jinja
        self.web_config = web_config
        self.user_gateway = user_gateway
        self.email_verification = email_verification
        self.token_registry = token_registry

    async def __call__(self, data: SendEmailVerificationCommand):
        user = await self.user_gateway.get_user_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        target_email = user.pending_email or user.email
        if target_email is None:
            raise UserHasNoEmail
        target_email = normalize_email(target_email)

        token = self.email_verification.generate_token(user_id=user.id)
        await self.token_registry.issue_email_verification_token(
            token=token,
            user_id=user.id,
            email=target_email,
            ttl_seconds=EMAIL_VERIFY_MAX_AGE_SECONDS,
        )

        verify_email_url = self.web_config.build_url(
            path="/verify-email",
            query_params={"token": token},
        )
        template = self.jinja.get_template("email_verification.jinja2")
        message_body = await template.render_async(
            {
                "username": user.username,
                "verify_email_url": verify_email_url,
            }
        )
        message = MessageSchema(
            subject="Подтвердите учётную запись",
            recipients=[NameEmail(name=user.username, email=target_email)],
            body=message_body,
            # Send HTML so the email client renders the button and clickable link.
            subtype=MessageType.html,
        )
        await self.mail.send_message(message)
