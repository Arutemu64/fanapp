from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import (
    EnvConfig,
)
from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.debug.config import DebugConfig
from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.push.config import PushConfig
from fanfan.application.interactors.notifications.config import NotificationConfig
from fanfan.application.interactors.outbox.config import OutboxConfig
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
    def get_mail_config(self, config: EnvConfig) -> MailConfig | None:
        return config.mail

    @provide
    def get_push_config(self, config: EnvConfig) -> PushConfig:
        return config.push

    @provide
    def get_outbox_config(self, config: EnvConfig) -> OutboxConfig:
        return config.outbox

    @provide
    def get_notification_config(self, config: EnvConfig) -> NotificationConfig:
        return config.notification
