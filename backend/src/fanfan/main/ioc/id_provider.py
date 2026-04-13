from dishka import Provider, Scope, provide

from fanfan.adapters.auth.providers.raw import RawIdProvider
from fanfan.adapters.auth.providers.web import WebIdProvider
from fanfan.application.ports.id_provider import IdProvider


class WebAuthProvider(Provider):
    scope = Scope.REQUEST

    web_id_provider = provide(WebIdProvider, provides=IdProvider)


class SystemAuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_system_id_provider(self) -> IdProvider:
        return RawIdProvider()
