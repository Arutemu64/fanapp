from fanfan.core.exceptions.base import AppException


class AuthenticationError(AppException):
    default_message = "Ошибка авторизации"


class UserNotAuthenticated(AuthenticationError):
    default_message = "Пользователь не авторизован"


class IncorrectPassword(AuthenticationError):
    default_message = "Неверный пароль"


class InvalidToken(AuthenticationError):
    default_message = "Неверный токен"


class TokenExpired(AuthenticationError):
    default_message = "Срок действия токена истек"


class RefreshTokenReused(AuthenticationError):
    default_message = "Refresh токен уже был использован"
