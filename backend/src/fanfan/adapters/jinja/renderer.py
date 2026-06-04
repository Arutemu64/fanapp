from typing import Any

from fanfan.adapters.jinja.factory import JinjaEnvironment
from fanfan.application.ports.template_renderer import TemplateRenderer


class JinjaTemplateRenderer(TemplateRenderer):
    def __init__(self, env: JinjaEnvironment):
        self._env = env

    async def render(self, template_name: str, context: dict[str, Any]) -> str:
        template = self._env.get_template(template_name)
        return await template.render_async(context)
