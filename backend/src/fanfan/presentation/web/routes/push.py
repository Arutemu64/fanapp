from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.push_sub.check_push_subscription import (
    CheckPushSubscription,
    CheckPushSubscriptionInput,
    CheckPushSubscriptionOutput,
)
from fanfan.application.interactors.push_sub.create_push_subscription import (
    CreatePushSubscription,
    CreatePushSubscriptionInput,
)
from fanfan.application.interactors.push_sub.delete_push_subscription import (
    DeletePushSubscription,
    DeletePushSubscriptionInput,
)
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ProblemDetails
from fanfan.presentation.web.security import session_security

push_router = APIRouter(
    tags=["Push"],
    prefix="/push",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@push_router.post(
    "",
    status_code=204,
    summary="Subscribe to push notifications",
    description="Registers a push subscription endpoint "
    "for the authenticated user's device.",
    responses={
        204: {"description": "Push subscription registered successfully."},
        409: {
            "model": ProblemDetails,
            "description": "Push subscription already exists.",
        },
    },
)
@inject
async def create_push_subscription(
    data: CreatePushSubscriptionInput, interactor: FromDishka[CreatePushSubscription]
) -> None:
    await interactor(data)


# The endpoint is a capability URL (RFC 8030 §8.3), so lookups and removals send
# it in a POST body: a path or query would put it in access logs.
@push_router.post(
    "/lookup",
    status_code=200,
    summary="Check push subscription",
    description="Reports whether the given endpoint is registered for the "
    "authenticated user. The client only needs this yes/no answer for its own "
    "device, so the full subscription list (incl. its keys) is not exposed. "
    "Read-only; a POST only to keep the endpoint out of the URL.",
    responses={
        200: {"description": "Subscription status for the endpoint."},
    },
)
@inject
async def check_push_subscription(
    data: CheckPushSubscriptionInput,
    interactor: FromDishka[CheckPushSubscription],
) -> CheckPushSubscriptionOutput:
    return await interactor(data)


@push_router.post(
    "/remove",
    summary="Unsubscribe from push notifications",
    description="Removes a push subscription endpoint for the authenticated user.",
    status_code=204,
    responses={
        204: {"description": "Push subscription removed successfully."},
        404: {
            "model": ProblemDetails,
            "description": "No subscription has this endpoint.",
        },
    },
)
@inject
async def delete_push_subscription(
    data: DeletePushSubscriptionInput,
    interactor: FromDishka[DeletePushSubscription],
) -> None:
    await interactor(data)
