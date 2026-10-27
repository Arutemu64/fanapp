from fanfan.core.exceptions.base import AppException, ConstraintViolation


class AuthenticationError(AppException):
    code = "AUTHENTICATION_ERROR"


class InvalidCredentials(AuthenticationError):
    code = "INVALID_CREDENTIALS"


class UserNotAuthenticated(AuthenticationError):
    code = "USER_NOT_AUTHENTICATED"


class IncorrectPassword(ConstraintViolation):
    code = "INCORRECT_PASSWORD"


class InvalidOtpCode(ConstraintViolation):
    code = "INVALID_OTP_CODE"


class InvalidTelegramAuthPayload(ConstraintViolation):
    code = "INVALID_TELEGRAM_AUTH_PAYLOAD"
