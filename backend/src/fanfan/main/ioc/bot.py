from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.notifications.telegram import TelegramNotifier
from fanfan.presentation.tgbot.config import TelegramConfig


class BotProvider(Provider):
    scope = Scope.APP

    @provide
    def get_bot_config(self, config: EnvConfig) -> TelegramConfig:
        return config.bot

    @provide
    async def get_bot(self, config: TelegramConfig) -> Bot:
        return Bot(
            token=config.token.get_secret_value(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    telegram_notifier = provide(TelegramNotifier, scope=scope.REQUEST)
