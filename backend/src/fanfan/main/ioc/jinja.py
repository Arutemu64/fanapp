from dishka import Provider, Scope, provide

from fanfan.adapters.jinja.factory import JinjaEnvironment, create_jinja_env


class JinjaProvider(Provider):
    scope = Scope.APP

    @provide
    def get_stream_jinja_env(self) -> JinjaEnvironment:
        return create_jinja_env()
