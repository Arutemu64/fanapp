from fanfan.core.exceptions.base import AppException, ConstraintViolation


class AuthenticationError(AppException):
    # 401 marker: the request lacks valid credentials.
    code = "AUTHENTICATION_ERROR"


class InvalidCredentials(AuthenticationError):
    code = "INVALID_CREDENTIALS"


class UserNotAuthenticated(AuthenticationError):
    code = "USER_NOT_AUTHENTICATED"


class IncorrectPassword(AuthenticationError):
    code = "INCORRECT_PASSWORD"


# An invalid/expired OTP is treated as bad input (400), not an auth failure, so
# it carries the ConstraintViolation marker rather than AuthenticationError.
class InvalidOtpCode(ConstraintViolation):
    code = "INVALID_OTP_CODE"


class InvalidTelegramAuthPayload(ConstraintViolation):
    code = "INVALID_TELEGRAM_AUTH_PAYLOAD"
