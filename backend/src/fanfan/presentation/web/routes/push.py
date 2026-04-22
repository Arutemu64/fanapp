from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.dto.push_sub import PushSubscriptionDTO
from fanfan.application.interactors.push_sub.create_push_subscriptions import (
    CreatePushSubscription,
    CreatePushSubscriptionInput,
)
from fanfan.application.interactors.push_sub.delete_user_push_subscription import (
    DeletePushSubscription,
    DeletePushSubscriptionInput,
)
from fanfan.application.interactors.push_sub.get_user_push_subscriptions import (
    ListUserPushSubscriptions,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

push_router = APIRouter(tags=["Push"], prefix="/push")


@push_router.post(
    "/",
    summary="Subscribe to push notifications",
    description="Registers a push subscription endpoint "
    "for the authenticated user's device.",
    responses={
        200: {"description": "Push subscription registered successfully."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
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
    summary="List push subscriptions",
    description="Returns a list of push subscriptions for the authenticated user.",
    responses={
        200: {"description": "List of push subscriptions."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
    },
)
@inject
async def list_subscriptions(
    interactor: FromDishka[ListUserPushSubscriptions],
) -> list[PushSubscriptionDTO]:
    return await interactor()


@push_router.delete(
    "/",
    summary="Unsubscribe from push notifications",
    description="Removes a push subscription endpoint for the authenticated user.",
    status_code=204,
    responses={
        204: {"description": "Push subscription removed successfully."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
        403: {"model": ErrorMessage, "description": "Access denied."},
    },
)
@inject
async def unsubscribe(
    data: DeletePushSubscriptionInput, interactor: FromDishka[DeletePushSubscription]
) -> None:
    await interactor(data)
