from dishka import Provider, Scope, provide
from pydantic_extra_types.timezone_name import TimeZoneName

from fanfan.adapters.jinja.factory import JinjaEnvironment, create_jinja_env
from fanfan.adapters.jinja.renderer import JinjaTemplateRenderer
from fanfan.application.ports.template_renderer import TemplateRenderer


class JinjaProvider(Provider):
    scope = Scope.APP

    @provide
    def get_stream_jinja_env(self, timezone: TimeZoneName) -> JinjaEnvironment:
        return create_jinja_env(timezone=timezone)

    @provide
    def get_template_renderer(self, env: JinjaEnvironment) -> TemplateRenderer:
        return JinjaTemplateRenderer(env)
