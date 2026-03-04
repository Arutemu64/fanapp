import uuid
from dataclasses import dataclass

from itsdangerous import URLSafeTimedSerializer

from fanfan.core.exceptions.auth import InvalidToken
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig

EMAIL_VERIFY_SALT = "email-verification-salt"
EMAIL_VERIFY_MAX_AGE_SECONDS = 3600


@dataclass(slots=True, frozen=True)
class EmailVerificationData:
    user_id: UserId
    nonce: str


class EmailVerificationService:
    def __init__(self, config: WebConfig):
        self.serializer = URLSafeTimedSerializer(config.secret_key.get_secret_value())

    def generate_token(self, user_id: UserId) -> tuple[str, str]:
        nonce = str(uuid.uuid4())
        token = self.serializer.dumps(
            {"user_id": user_id, "nonce": nonce},
            salt=EMAIL_VERIFY_SALT,
        )
        return token, nonce

    def verify_token(self, token: str) -> EmailVerificationData:
        payload = self.serializer.loads(
            token,
            salt=EMAIL_VERIFY_SALT,
            max_age=EMAIL_VERIFY_MAX_AGE_SECONDS,
        )

        try:
            user_id = UserId(payload["user_id"])
            nonce = str(payload["nonce"])
        except (TypeError, ValueError, KeyError) as e:
            raise InvalidToken from e

        return EmailVerificationData(user_id=user_id, nonce=nonce)
