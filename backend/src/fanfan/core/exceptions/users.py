from fanfan.core.exceptions.base import AppException


class UsersException(AppException):
    pass


class UserNotFound(UsersException):
    default_message = "Пользователь не найден"


class UserAlreadyExists(UsersException):
    default_message = "Пользователь уже существует"


class UsernameAlreadyTaken(UsersException):
    default_message = "Имя пользователя занято"


class UserHasNoEmail(UsersException):
    default_message = "У пользователя нет почтового адреса"


class EmailAlreadyExists(UsersException):
    default_message = "Этот адрес электронной почты уже используется"
