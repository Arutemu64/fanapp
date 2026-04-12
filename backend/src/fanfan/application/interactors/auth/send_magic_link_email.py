from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, NameEmail

from fanfan.adapters.jinja.factory import StreamJinjaEnvironment
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_login import (
    EMAIL_MAGIC_LINK_MAX_AGE_SECONDS,
    EmailService,
)
from fanfan.core.utils.email import normalize_email
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class SendMagicLinkEmailInput(BaseModel):
    user_id: UserId


class SendMagicLinkEmail:
    def __init__(
        self,
        user_repo: UserRepository,
        email_login: EmailService,
        web_config: WebConfig,
        mail: FastMail,
        jinja: StreamJinjaEnvironment,
        token_registry: TokenRegistry,
    ):
        self.mail = mail
        self.jinja = jinja
        self.web_config = web_config
        self.user_repo = user_repo
        self.email_login = email_login
        self.token_registry = token_registry

    async def __call__(self, data: SendMagicLinkEmailInput) -> None:
        user = await self.user_repo.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        if user.email is None:
            raise UserHasNoEmail
        normalized_email = normalize_email(user.email)

        token = self.email_login.generate_login_token(user_id=user.id)
        await self.token_registry.issue_email_login_token(
            token=token,
            user_id=user.id,
            email=normalized_email,
            ttl_seconds=EMAIL_MAGIC_LINK_MAX_AGE_SECONDS,
        )

        magic_login_url = self.web_config.build_url(
            path="/email-login",
            query_params={"token": token},
        )
        template = self.jinja.get_template("email_magic_link.jinja2")
        message_body = await template.render_async(
            {
                "username": user.username,
                "magic_login_url": magic_login_url,
            }
        )
        message = MessageSchema(
            subject="Ссылка для входа в FAN App",
            recipients=[NameEmail(name=user.username, email=normalized_email)],
            body=message_body,
            # Send HTML so the email client renders the button and clickable link.
            subtype=MessageType.html,
        )
        await self.mail.send_message(message)
