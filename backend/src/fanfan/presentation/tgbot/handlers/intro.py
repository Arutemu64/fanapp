from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dishka.integrations.aiogram import FromDishka, inject

from fanfan.presentation.web.config import WebConfig

router = Router(name="intro")

# The bot has no in-app features of its own: every interaction just points the
# user back to the web app. The copy is intentionally short — audience is teen
# to young adult, non-technical.
INTRO_TEXT = (
    "Привет! Это бот-компаньон конвента FAN FAN. Всё самое важное — "
    "расписание, голосования и новости — теперь в веб-приложении.\n\n"
    "Открой его по кнопке ниже 👇"
)


def _intro_markup(web_config: WebConfig) -> InlineKeyboardMarkup:
    # A plain URL button (not a Web App button): it opens the app in the
    # browser rather than the in-Telegram webview.
    url = web_config.build_url("/")
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🌐 Открыть приложение", url=url)]]
    )


# DM-only: filtering on the private chat type means group and channel updates
# never match, so the bot stays silent everywhere except direct messages.
@router.message(F.chat.type == ChatType.PRIVATE)
@inject
async def intro_message(message: Message, web_config: FromDishka[WebConfig]) -> None:
    await message.answer(INTRO_TEXT, reply_markup=_intro_markup(web_config))


@router.callback_query(F.message.chat.type == ChatType.PRIVATE)
@inject
async def intro_callback(
    callback: CallbackQuery,
    bot: FromDishka[Bot],
    web_config: FromDishka[WebConfig],
) -> None:
    # Acknowledge the callback so the client stops its loading spinner, then
    # send the intro. Address the DM by the sender's id (always present) rather
    # than callback.message, which may be an InaccessibleMessage. In a private
    # chat the user id is the chat id.
    await callback.answer()
    await bot.send_message(
        chat_id=callback.from_user.id,
        text=INTRO_TEXT,
        reply_markup=_intro_markup(web_config),
    )
