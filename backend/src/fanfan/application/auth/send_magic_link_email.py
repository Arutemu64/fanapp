from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, NameEmail

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.jinja.factory import StreamJinjaEnvironment
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_login import (
    EMAIL_MAGIC_LINK_MAX_AGE_SECONDS,
    EmailLoginService,
)
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class SendMagicLinkEmailCommand(BaseModel):
    user_id: UserId


class SendMagicLinkEmail:
    def __init__(
        self,
        user_gateway: UserGateway,
        email_login: EmailLoginService,
        web_config: WebConfig,
        mail: FastMail,
        jinja: StreamJinjaEnvironment,
        token_registry: RedisAuthTokenRegistry,
    ):
        self.mail = mail
        self.jinja = jinja
        self.web_config = web_config
        self.user_gateway = user_gateway
        self.email_login = email_login
        self.token_registry = token_registry

    async def __call__(self, data: SendMagicLinkEmailCommand):
        user = await self.user_gateway.get_user_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        if user.email is None:
            raise UserHasNoEmail

        token = self.email_login.generate_token(user_id=user.id)
        await self.token_registry.issue_email_login_token(
            token=token,
            user_id=user.id,
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
            recipients=[NameEmail(name=user.username, email=user.email)],
            body=message_body,
            subtype=MessageType.plain,
        )
        await self.mail.send_message(message)
