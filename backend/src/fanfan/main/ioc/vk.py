from dishka import Provider, Scope, provide
from vkbottle.api import API

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.vk.config import VkConfig
from fanfan.adapters.vk.notifier import VkNotifier
from fanfan.application.ports.notifier import VkNotifierPort


class VkProvider(Provider):
    scope = Scope.APP

    @provide
    def get_vk_config(self, config: EnvConfig) -> VkConfig:
        return config.vk

    @provide
    def get_vk_api(self, config: VkConfig) -> API:
        return API(token=config.group_token.get_secret_value())

    vk_notifier = provide(VkNotifier, scope=Scope.REQUEST, provides=VkNotifierPort)
