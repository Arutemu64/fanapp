from fastapi import APIRouter

from fanfan.presentation.web.responses import VALIDATION_RESPONSES
from fanfan.presentation.web.routes.auth import auth_router
from fanfan.presentation.web.routes.current_user import current_user_router
from fanfan.presentation.web.routes.debug import debug_router
from fanfan.presentation.web.routes.feedback import feedback_router
from fanfan.presentation.web.routes.notifications import notifications_router
from fanfan.presentation.web.routes.push import push_router
from fanfan.presentation.web.routes.schedule import schedule_router
from fanfan.presentation.web.routes.settings import settings_router
from fanfan.presentation.web.routes.sse import sse_router
from fanfan.presentation.web.routes.voting import voting_router
from fanfan.presentation.web.routes.webhooks import webhooks_router


def setup_api_router() -> APIRouter:
    router = APIRouter()

    # 401/403 are not global: routes that need a session declare the SessionCookie
    # security marker and AUTH_RESPONSES themselves, so public routes stay clean.
    router.include_router(debug_router, responses=VALIDATION_RESPONSES)
    router.include_router(auth_router, responses=VALIDATION_RESPONSES)
    router.include_router(current_user_router, responses=VALIDATION_RESPONSES)
    router.include_router(settings_router, responses=VALIDATION_RESPONSES)
    router.include_router(sse_router, responses=VALIDATION_RESPONSES)
    router.include_router(schedule_router, responses=VALIDATION_RESPONSES)
    router.include_router(voting_router, responses=VALIDATION_RESPONSES)
    router.include_router(webhooks_router, responses=VALIDATION_RESPONSES)
    router.include_router(notifications_router, responses=VALIDATION_RESPONSES)
    router.include_router(push_router, responses=VALIDATION_RESPONSES)
    router.include_router(feedback_router, responses=VALIDATION_RESPONSES)

    return router
