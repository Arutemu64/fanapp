from aiogram import Router

from fanfan.presentation.tgbot.handlers.intro import router as intro_router


def setup_router() -> Router:
    router = Router()

    router.include_router(intro_router)

    return router
