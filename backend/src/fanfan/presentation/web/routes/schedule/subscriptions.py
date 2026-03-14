from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.subscriptions.create_subscription import (
    CreateSubscription,
    CreateSubscriptionCommand,
)
from fanfan.application.subscriptions.delete_subscription import (
    DeleteSubscription,
    DeleteSubscriptionCommand,
)
from fanfan.core.dto.subscription import SubscriptionFullDTO
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.exceptions.subscriptions import (
    SubscriptionAlreadyExist,
    SubscriptionNotFound,
)
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.presentation.web.schemas.error import ErrorMessage

subscriptions_router = APIRouter(prefix="/subscriptions")


@subscriptions_router.post(
    "",
    status_code=201,
    summary="Create a new event subscription",
    description="Subscribes the current user to a specific schedule event. "
    "Prevents duplicate subscriptions.",
    responses={
        201: {
            "model": SubscriptionFullDTO,
            "description": "Subscription created successfully.",
        },
        404: {"model": ErrorMessage, "description": "Event ID does not exist."},
        409: {
            "model": ErrorMessage,
            "description": "Subscription for this event already exists.",
        },
    },
)
@inject
async def new_subscription(
    data: CreateSubscriptionCommand,
    interactor: FromDishka[CreateSubscription],
) -> SubscriptionFullDTO:
    try:
        return await interactor(data)
    except EventNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except SubscriptionAlreadyExist as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=e.message
        ) from e


@subscriptions_router.delete(
    "/{subscription_id}",
    status_code=204,
    summary="Remove a subscription",
    description="Deletes an existing subscription by its unique ID.",
    responses={
        204: {"description": "Subscription deleted successfully."},
        404: {
            "model": ErrorMessage,
            "description": "Subscription ID not found.",
        },
    },
)
@inject
async def delete_subscription(
    subscription_id: SubscriptionId,
    interactor: FromDishka[DeleteSubscription],
) -> None:
    try:
        await interactor(DeleteSubscriptionCommand(subscription_id=subscription_id))
    except SubscriptionNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
