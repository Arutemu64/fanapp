from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.tgbot.client import TelegramApiClient
from fanfan.adapters.tgbot.config import TelegramConfig
from fanfan.adapters.tgbot.notifier import TelegramNotifier, TelegramRateLimiter
from fanfan.application.ports.notifier import TelegramNotifierPort

TELEGRAM_TIMEOUT = httpx2.Timeout(30.0, connect=10.0)


class TelegramProvider(Provider):
    scope = Scope.APP

    @provide
    def get_bot_config(self, config: EnvConfig) -> TelegramConfig:
        return config.bot

    @provide
    async def get_telegram_api_client(
        self, config: TelegramConfig
    ) -> AsyncIterable[TelegramApiClient]:
        async with httpx2.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
            yield TelegramApiClient(client=client, config=config)

    rate_limiter = provide(TelegramRateLimiter)

    telegram_notifier = provide(
        TelegramNotifier, scope=Scope.REQUEST, provides=TelegramNotifierPort
    )
