from dishka import Provider, Scope, provide
from pydantic_extra_types.timezone_name import TimeZoneName

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.debug.config import DebugConfig
from fanfan.presentation.web.config import WebConfig


class ConfigProvider(Provider):
    """Root config plus the cross-cutting slices consumed app-wide.

    Domain-specific slices are unpacked by the provider that owns the domain
    (mail -> MailProvider, push -> PushProvider, nats -> StreamProvider, ...),
    so a factory never depends on the whole EnvConfig aggregate. Only genuinely
    cross-cutting leaves (web, debug, timezone) stay here alongside the root.
    """

    scope = Scope.APP

    @provide
    def get_config(self) -> EnvConfig:
        return get_config()

    @provide
    def get_web_config(self, config: EnvConfig) -> WebConfig:
        return config.web

    @provide
    def get_debug_config(self, config: EnvConfig) -> DebugConfig:
        return config.debug

    @provide
    def get_timezone(self, config: EnvConfig) -> TimeZoneName:
        return config.timezone
