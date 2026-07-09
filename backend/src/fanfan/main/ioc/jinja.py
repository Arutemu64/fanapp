from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.jinja.factory import JinjaEnvironment, create_jinja_env
from fanfan.adapters.jinja.renderer import JinjaTemplateRenderer
from fanfan.application.ports.template_renderer import TemplateRenderer


class JinjaProvider(Provider):
    scope = Scope.APP

    @provide
    def get_stream_jinja_env(self, config: EnvConfig) -> JinjaEnvironment:
        return create_jinja_env(timezone=config.timezone)

    @provide
    def get_template_renderer(self, env: JinjaEnvironment) -> TemplateRenderer:
        return JinjaTemplateRenderer(env)
