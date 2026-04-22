from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.subscriptions.create_subscription import (
    CreateSubscription,
    CreateSubscriptionInput,
    CreateSubscriptionOutput,
)
from fanfan.application.interactors.subscriptions.delete_subscription import (
    DeleteSubscription,
    DeleteSubscriptionInput,
)
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.presentation.web.schemas.error import ErrorMessage

subscriptions_router = APIRouter(prefix="/subscriptions")


@subscriptions_router.post(
    "/",
    status_code=201,
    summary="Create a new event subscription",
    description="Subscribes the current user to a specific schedule event. "
    "Prevents duplicate subscriptions.",
    responses={
        201: {
            "model": CreateSubscriptionOutput,
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
    data: CreateSubscriptionInput,
    interactor: FromDishka[CreateSubscription],
) -> CreateSubscriptionOutput:
    return await interactor(data)


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
    await interactor(DeleteSubscriptionInput(subscription_id=subscription_id))
