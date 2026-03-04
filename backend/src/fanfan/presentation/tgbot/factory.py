from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from fanfan.presentation.tgbot.config import BotConfig


def create_bot(config: BotConfig) -> Bot:
    return Bot(
        token=config.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
