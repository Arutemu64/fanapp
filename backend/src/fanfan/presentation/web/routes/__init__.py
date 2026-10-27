from fastapi import APIRouter

from fanfan.presentation.web.responses import VALIDATION_RESPONSES
from fanfan.presentation.web.routes.auth import auth_router
from fanfan.presentation.web.routes.config import config_router
from fanfan.presentation.web.routes.current_user import current_user_router
from fanfan.presentation.web.routes.debug import debug_router
from fanfan.presentation.web.routes.feedback import feedback_router
from fanfan.presentation.web.routes.notifications import notifications_router
from fanfan.presentation.web.routes.push import push_router
from fanfan.presentation.web.routes.quest import quest_router
from fanfan.presentation.web.routes.schedule import schedule_router
from fanfan.presentation.web.routes.settings import settings_router
from fanfan.presentation.web.routes.sse import sse_router
from fanfan.presentation.web.routes.sync import sync_router
from fanfan.presentation.web.routes.tickets import (
    ticket_batches_router,
    tickets_router,
)
from fanfan.presentation.web.routes.users import users_router
from fanfan.presentation.web.routes.voting import voting_router
from fanfan.presentation.web.routes.webhooks import webhooks_router


def setup_api_router() -> APIRouter:
    router = APIRouter()

    router.include_router(debug_router, responses=VALIDATION_RESPONSES)
    router.include_router(auth_router, responses=VALIDATION_RESPONSES)
    router.include_router(config_router, responses=VALIDATION_RESPONSES)
    router.include_router(current_user_router, responses=VALIDATION_RESPONSES)
    router.include_router(settings_router, responses=VALIDATION_RESPONSES)
    router.include_router(sse_router, responses=VALIDATION_RESPONSES)
    router.include_router(schedule_router, responses=VALIDATION_RESPONSES)
    router.include_router(voting_router, responses=VALIDATION_RESPONSES)
    router.include_router(webhooks_router, responses=VALIDATION_RESPONSES)
    router.include_router(notifications_router, responses=VALIDATION_RESPONSES)
    router.include_router(push_router, responses=VALIDATION_RESPONSES)
    router.include_router(feedback_router, responses=VALIDATION_RESPONSES)
    router.include_router(tickets_router, responses=VALIDATION_RESPONSES)
    router.include_router(ticket_batches_router, responses=VALIDATION_RESPONSES)
    router.include_router(sync_router, responses=VALIDATION_RESPONSES)
    router.include_router(users_router, responses=VALIDATION_RESPONSES)
    router.include_router(quest_router, responses=VALIDATION_RESPONSES)

    return router
