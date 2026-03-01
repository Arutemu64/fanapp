from dishka import Provider, Scope, provide

from fanfan.adapters.auth.providers.bot import BotIdProvider
from fanfan.adapters.auth.providers.raw import RawIdProvider
from fanfan.adapters.auth.providers.web import (
    OAuth2PasswordBearerWithCookie,
    WebIdProvider,
)
from fanfan.adapters.auth.utils.jwt import JwtTokenProcessor
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.vo.user import UserId


class JwtTokenProcessorProvider(Provider):
    token_processor = provide(JwtTokenProcessor, scope=Scope.APP)


class BotAuthProvider(Provider):
    scope = Scope.REQUEST

    bot_id_provider = provide(BotIdProvider, provides=IdProvider)


class WebAuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_oauth2_scheme(self) -> OAuth2PasswordBearerWithCookie:
        return OAuth2PasswordBearerWithCookie(tokenUrl="/auth/token", auto_error=False)

    web_id_provider = provide(WebIdProvider, provides=IdProvider)


class SystemAuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_system_id_provider(self, user_gateway: UserGateway) -> IdProvider:
        return RawIdProvider(user_id=UserId(0), user_gateway=user_gateway)
