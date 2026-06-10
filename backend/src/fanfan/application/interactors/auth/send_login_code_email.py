from pydantic import BaseModel

from fanfan.application.ports.email_sender import (
    EmailMessage,
    EmailRecipient,
    EmailSender,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.template_renderer import TemplateRenderer
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_login import (
    EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
    generate_numeric_code,
)
from fanfan.core.vo.user import UserId


class SendLoginCodeEmailInput(BaseModel):
    user_id: UserId


class SendLoginCodeEmail:
    def __init__(
        self,
        user_gateway: UserGateway,
        email_sender: EmailSender,
        template_renderer: TemplateRenderer,
        token_registry: TokenRegistry,
    ):
        self.email_sender = email_sender
        self.template_renderer = template_renderer
        self.user_gateway = user_gateway
        self.token_registry = token_registry

    async def __call__(self, data: SendLoginCodeEmailInput) -> None:
        user = await self.user_gateway.get_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        if user.email is None:
            raise UserHasNoEmail
        email_value = user.email.value

        code = generate_numeric_code()
        await self.token_registry.issue_email_login_code(
            user_id=user.id,
            email=email_value,
            code=code,
            ttl_seconds=EMAIL_LOGIN_CODE_MAX_AGE_SECONDS,
        )

        message_body = await self.template_renderer.render(
            "email_login_code.jinja2",
            {
                "username": user.username,
                "login_code": code,
                "expires_in_minutes": max(1, EMAIL_LOGIN_CODE_MAX_AGE_SECONDS // 60),
            },
        )
        message = EmailMessage(
            subject="Код входа в FAN FAN",
            recipients=[EmailRecipient(name=user.username or "", email=email_value)],
            html_body=message_body,
        )
        await self.email_sender.send(message)
