from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.vk.config import VkConfig
from fanfan.adapters.vk.notifier import VkNotifier
from fanfan.application.ports.notifier import VkNotifierPort


class VkProvider(Provider):
    scope = Scope.APP

    @provide
    def get_vk_config(self, config: EnvConfig) -> VkConfig:
        return config.vk

    # The notifier opens its own httpx2 client per send (see VkNotifier), so no
    # bare AsyncClient is exposed as a container-wide dependency.
    vk_notifier = provide(VkNotifier, scope=Scope.REQUEST, provides=VkNotifierPort)
