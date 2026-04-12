import secrets

from fanfan.core.vo.user import UserId

EMAIL_MAGIC_LINK_MAX_AGE_SECONDS = 900
EMAIL_VERIFY_MAX_AGE_SECONDS = 3600


class EmailService:
    @staticmethod
    def generate_login_token(user_id: UserId) -> str:
        _ = user_id
        return secrets.token_urlsafe(16)

    @staticmethod
    def generate_verification_token(user_id: UserId) -> str:
        _ = user_id
        return secrets.token_urlsafe(16)
