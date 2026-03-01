from dishka import Provider, Scope, provide

from fanfan.adapters.jinja.factory import StreamJinjaEnvironment, create_stream_jinja


class JinjaProvider(Provider):
    scope = Scope.APP

    @provide
    def get_stream_jinja_env(self) -> StreamJinjaEnvironment:
        return create_stream_jinja()
