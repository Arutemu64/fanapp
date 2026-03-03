from itsdangerous import URLSafeTimedSerializer

from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig

EMAIL_VERIFY_SALT = "email-verification-salt"
EMAIL_VERIFY_MAX_AGE_SECONDS = 3600


class EmailVerificationService:
    def __init__(self, config: WebConfig):
        self.serializer = URLSafeTimedSerializer(config.secret_key.get_secret_value())

    def generate_token(self, user_id: UserId) -> str:
        return self.serializer.dumps(user_id, salt=EMAIL_VERIFY_SALT)

    def verify_token(self, token: str) -> UserId:
        user_id = self.serializer.loads(
            token,
            salt=EMAIL_VERIFY_SALT,
            max_age=EMAIL_VERIFY_MAX_AGE_SECONDS,
        )
        return UserId(user_id)
