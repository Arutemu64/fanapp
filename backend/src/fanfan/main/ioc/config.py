from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import (
    EnvConfig,
)
from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.debug.config import DebugConfig
from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.push.config import PushConfig
from fanfan.presentation.web.config import WebConfig


class ConfigProvider(Provider):
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
    def get_mail_config(self, config: EnvConfig) -> MailConfig:
        return config.mail

    @provide
    def get_push_config(self, config: EnvConfig) -> PushConfig:
        return config.push
