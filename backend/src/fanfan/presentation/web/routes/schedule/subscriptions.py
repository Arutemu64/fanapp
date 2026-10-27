from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path, Response

from fanfan.application.interactors.subscriptions.create_subscription import (
    CreateSubscription,
    CreateSubscriptionInput,
    CreateSubscriptionOutput,
)
from fanfan.application.interactors.subscriptions.delete_subscription import (
    DeleteSubscription,
    DeleteSubscriptionInput,
)
from fanfan.application.interactors.subscriptions.list_subscriptions import (
    ListSubscriptions,
    ListSubscriptionsOutput,
)
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.presentation.web.responses import AUTH_RESPONSES, location_header
from fanfan.presentation.web.schemas.error import ProblemDetails
from fanfan.presentation.web.security import session_security

subscriptions_router = APIRouter(
    prefix="/subscriptions",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@subscriptions_router.get(
    "",
    summary="List the current user's subscriptions",
    description="Returns every schedule event the current user is subscribed to. "
    "Served separately from the schedule so the schedule itself stays universal "
    "and cacheable offline.",
)
@inject
async def list_subscriptions(
    interactor: FromDishka[ListSubscriptions],
) -> ListSubscriptionsOutput:
    return await interactor()


@subscriptions_router.post(
    "",
    status_code=201,
    summary="Create a new event subscription",
    description="Subscribes the current user to a specific schedule event. "
    "Prevents duplicate subscriptions.",
    responses={
        201: {
            "description": "Subscription created successfully.",
            "headers": location_header("The created subscription."),
        },
        404: {"model": ProblemDetails, "description": "Event ID does not exist."},
        409: {
            "model": ProblemDetails,
            "description": "Subscription for this event already exists.",
        },
    },
)
@inject
async def create_subscription(
    data: CreateSubscriptionInput,
    response: Response,
    interactor: FromDishka[CreateSubscription],
) -> CreateSubscriptionOutput:
    created = await interactor(data)
    response.headers["Location"] = f"/schedule/subscriptions/{created.subscription_id}"
    return created


@subscriptions_router.delete(
    "/{subscription_id}",
    status_code=204,
    summary="Remove a subscription",
    description="Deletes an existing subscription by its unique ID.",
    responses={
        204: {"description": "Subscription deleted successfully."},
        404: {
            "model": ProblemDetails,
            "description": "Subscription ID not found.",
        },
    },
)
@inject
async def delete_subscription(
    subscription_id: Annotated[
        SubscriptionId,
        Path(description="Subscription ID to remove."),
    ],
    interactor: FromDishka[DeleteSubscription],
) -> None:
    await interactor(DeleteSubscriptionInput(subscription_id=subscription_id))
