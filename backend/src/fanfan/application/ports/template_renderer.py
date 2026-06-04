from typing import Any, Protocol


class TemplateRenderer(Protocol):
    async def render(self, template_name: str, context: dict[str, Any]) -> str: ...
