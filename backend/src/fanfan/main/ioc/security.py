from dishka import Provider, Scope, provide

from fanfan.adapters.auth.password_hasher import PwdlibPasswordHasher
from fanfan.application.ports.password_hasher import PasswordHasher


class SecurityProvider(Provider):
    scope = Scope.APP

    password_hasher = provide(PwdlibPasswordHasher, provides=PasswordHasher)
