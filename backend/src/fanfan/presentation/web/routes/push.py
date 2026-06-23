from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query
from pydantic import BaseModel

from fanfan.application.interactors.push_sub.check_push_subscription import (
    CheckPushSubscription,
    CheckPushSubscriptionInput,
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
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.security import session_security

push_router = APIRouter(
    tags=["Push"],
    prefix="/push",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


class PushSubscriptionStatus(BaseModel):
    subscribed: bool


@push_router.post(
    "/",
    summary="Subscribe to push notifications",
    description="Registers a push subscription endpoint "
    "for the authenticated user's device.",
    responses={
        200: {"description": "Push subscription registered successfully."},
        409: {
            "model": ErrorMessage,
            "description": "Push subscription already exists.",
        },
    },
)
@inject
async def subscribe(
    data: CreatePushSubscriptionInput, interactor: FromDishka[CreatePushSubscription]
) -> None:
    await interactor(data)


@push_router.get(
    "/",
    summary="Check push subscription",
    description="Reports whether the given endpoint is registered for the "
    "authenticated user. The client only needs this yes/no answer for its own "
    "device, so the full subscription list (incl. its keys) is not exposed.",
    responses={
        200: {"description": "Subscription status for the endpoint."},
    },
)
@inject
async def check_subscription(
    endpoint: Annotated[str, Query()],
    interactor: FromDishka[CheckPushSubscription],
) -> PushSubscriptionStatus:
    subscribed = await interactor(CheckPushSubscriptionInput(endpoint=endpoint))
    return PushSubscriptionStatus(subscribed=subscribed)


@push_router.delete(
    "/",
    summary="Unsubscribe from push notifications",
    description="Removes a push subscription endpoint for the authenticated user.",
    status_code=204,
    responses={
        204: {"description": "Push subscription removed successfully."},
    },
)
@inject
async def unsubscribe(
    data: DeletePushSubscriptionInput, interactor: FromDishka[DeletePushSubscription]
) -> None:
    await interactor(data)
