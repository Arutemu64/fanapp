from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, NameEmail

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.core.exceptions.users import UserHasNoEmail, UserNotFound
from fanfan.core.services.email_verification import EmailVerificationService
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
    ):
        self.mail = mail
        self.web_config = web_config
        self.user_gateway = user_gateway
        self.email_verification = email_verification

    async def __call__(self, data: SendEmailVerificationCommand):
        user = await self.user_gateway.get_user_by_id(data.user_id)
        if user is None:
            raise UserNotFound
        if user.email is None:
            raise UserHasNoEmail
        token = self.email_verification.generate_token(user_id=user.id)
        verify_email_url = f"{self.web_config.base_url}/verify-email?token={token}"
        message_body = (
            f"Для подтверждения учётной записи перейдите по ссылке: {verify_email_url}"
        )
        message = MessageSchema(
            subject="Подтвердите учётную запись",
            recipients=[NameEmail(name=user.username, email=user.email)],
            body=message_body,
            subtype=MessageType.plain,
        )
        await self.mail.send_message(message)
