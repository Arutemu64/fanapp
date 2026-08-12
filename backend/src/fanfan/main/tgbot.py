import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import MenuButtonDefault
from dishka.integrations.aiogram import setup_dishka

from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.tgbot.handlers import setup_router

logger = logging.getLogger(__name__)


async def _on_startup(bot: Bot) -> None:
    # Drop any stale webhook (this process uses long polling) and discard
    # updates queued while the bot was offline — the reply is stateless, so
    # replaying a backlog only spams users.
    await bot.delete_webhook(drop_pending_updates=True)

    # The bot exposes no commands and no custom menu button: strip both so a
    # previously configured menu (e.g. a Web App button) does not linger.
    # delete_my_commands / MenuButtonDefault target the default scope — all
    # users, every chat.
    await bot.delete_my_commands()
    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())

    logger.info("Telegram bot started (long polling)")


async def run() -> None:
    container = create_system_container()
    bot = await container.get(Bot)

    dp = Dispatcher()
    dp.include_router(setup_router())
    dp.startup.register(_on_startup)
    setup_dishka(container, dp)

    try:
        # start_polling blocks until SIGINT/SIGTERM, which it handles itself.
        await dp.start_polling(bot)
    finally:
        await container.close()


def main() -> None:
    init(service_name="bot")
    asyncio.run(run())


if __name__ == "__main__":
    main()
