from fanfan.core.exceptions.base import AppException


class AuthenticationError(AppException):
    code = "AUTHENTICATION_ERROR"


class InvalidCredentials(AuthenticationError):
    code = "INVALID_CREDENTIALS"


class UserNotAuthenticated(AuthenticationError):
    code = "USER_NOT_AUTHENTICATED"


class IncorrectPassword(AuthenticationError):
    code = "INCORRECT_PASSWORD"


class InvalidOtpCode(AuthenticationError):
    code = "INVALID_OTP_CODE"


class InvalidTelegramAuthPayload(AppException):
    code = "INVALID_TELEGRAM_AUTH_PAYLOAD"
