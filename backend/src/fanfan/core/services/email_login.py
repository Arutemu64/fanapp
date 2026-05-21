import secrets

from fanfan.core.vo.user import UserId

EMAIL_LOGIN_CODE_MAX_AGE_SECONDS = 900
EMAIL_CONFIRMATION_CODE_MAX_AGE_SECONDS = 3600
EMAIL_OTP_LENGTH = 6
EMAIL_CODE_REQUEST_COOLDOWN_SECONDS = 60


class EmailService:
    @staticmethod
    def _generate_numeric_code() -> str:
        # Keep the code short enough for mobile input, but still random.
        return f"{secrets.randbelow(10**EMAIL_OTP_LENGTH):0{EMAIL_OTP_LENGTH}d}"

    @staticmethod
    def generate_login_code(user_id: UserId) -> str:
        _ = user_id
        return EmailService._generate_numeric_code()

    @staticmethod
    def generate_confirmation_code(user_id: UserId) -> str:
        _ = user_id
        return EmailService._generate_numeric_code()
