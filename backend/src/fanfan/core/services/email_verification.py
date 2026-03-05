import secrets

from fanfan.core.vo.user import UserId

EMAIL_VERIFY_MAX_AGE_SECONDS = 3600


class EmailVerificationService:
    def generate_token(self, user_id: UserId) -> str:
        _ = user_id
        return secrets.token_urlsafe(16)
