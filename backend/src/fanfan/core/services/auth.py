from fastapi_mail import FastMail, MessageSchema, MessageType
from itsdangerous import URLSafeTimedSerializer
from pwdlib import PasswordHash
from pydantic import NameEmail

from fanfan.adapters.auth.utils.jwt import JwtTokenProcessor
from fanfan.core.dto.token import Token
from fanfan.core.exceptions.users import UserHasNoEmail
from fanfan.core.models.user import User
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig

EMAIL_VERIFY_SALT = "email-verification-salt"


class AuthService:
    def __init__(
        self,
        config: WebConfig,
        mail: FastMail,
        web_config: WebConfig,
        jwt: JwtTokenProcessor,
    ):
        self.jwt = jwt
        self.web_config = web_config
        self.mail = mail
        self.password_hash = PasswordHash.recommended()
        self.serializer = URLSafeTimedSerializer(config.secret_key.get_secret_value())

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        return self.password_hash.verify(password, hashed_password)

    def create_token(self, user_id: UserId) -> Token:
        access_token = self.jwt.create_access_token(user_id=user_id)
        refresh_token = self.jwt.create_refresh_token(user_id=user_id)
        return Token(
            access_token=access_token, refresh_token=refresh_token, token_type="Bearer"
        )

    def generate_signature(self, user_id: UserId, salt: str) -> str:
        return self.serializer.dumps(user_id, salt=salt)

    def verify_signature(self, token: str, salt: str, max_age: int) -> UserId:
        user_id = self.serializer.loads(token, salt=salt, max_age=max_age)
        return UserId(user_id)

    async def send_verification_email(self, user: User):
        if user.email is None:
            raise UserHasNoEmail
        token = self.generate_signature(user_id=user.id, salt=EMAIL_VERIFY_SALT)
        message_body = (
            f"Для подтверждения учётной записи "
            f"перейдите по ссылке: {self.web_config.host}/verify-email?token={token}"
        )
        message = MessageSchema(
            subject="Подтвердите учётную запись",
            recipients=[NameEmail(name=user.username, email=user.email)],
            body=message_body,
            subtype=MessageType.plain,
        )
        await self.mail.send_message(message)
