import secrets

from fanfan.core.vo.user import UserId

EMAIL_MAGIC_LINK_MAX_AGE_SECONDS = 900


class EmailLoginService:
    def generate_token(self, user_id: UserId) -> str:
        _ = user_id
        return secrets.token_urlsafe(16)
