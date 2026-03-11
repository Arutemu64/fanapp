from fastapi import APIRouter
from starlette import status

from fanfan.presentation.web.routes.auth import auth_router
from fanfan.presentation.web.routes.current_user import current_user_router
from fanfan.presentation.web.routes.notifications import notifications_router
from fanfan.presentation.web.routes.push import push_router
from fanfan.presentation.web.routes.schedule import schedule_router
from fanfan.presentation.web.routes.sse import sse_router
from fanfan.presentation.web.routes.voting import voting_router
from fanfan.presentation.web.routes.webhooks import webhooks_router
from fanfan.presentation.web.schemas.error import ErrorMessage, ValidationErrorResponse


def setup_api_router() -> APIRouter:
    router = APIRouter()

    common_responses = {
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorMessage,
            "description": "Not authenticated.",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorMessage,
            "description": "Access denied.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ValidationErrorResponse,
            "description": "Request validation error.",
        },
    }

    router.include_router(auth_router, responses=common_responses)
    router.include_router(current_user_router, responses=common_responses)
    router.include_router(sse_router, responses=common_responses)
    router.include_router(schedule_router, responses=common_responses)
    router.include_router(voting_router, responses=common_responses)
    router.include_router(webhooks_router, responses=common_responses)
    router.include_router(notifications_router, responses=common_responses)
    router.include_router(push_router, responses=common_responses)

    return router
