from dishka import Provider, Scope, provide

from fanfan.adapters.auth.jwt import JwtTokenProcessor
from fanfan.adapters.auth.providers.raw import RawIdProvider
from fanfan.adapters.auth.providers.web import (
    OAuth2PasswordBearerWithCookie,
    WebIdProvider,
)
from fanfan.application.ports.id_provider import IdProvider


class JwtTokenProcessorProvider(Provider):
    token_processor = provide(JwtTokenProcessor, scope=Scope.APP)


class WebAuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_oauth2_scheme(self) -> OAuth2PasswordBearerWithCookie:
        return OAuth2PasswordBearerWithCookie(tokenUrl="/auth/token", auto_error=False)

    web_id_provider = provide(WebIdProvider, provides=IdProvider)


class SystemAuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_system_id_provider(self) -> IdProvider:
        return RawIdProvider()
