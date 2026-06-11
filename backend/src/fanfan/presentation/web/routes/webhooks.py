import secrets

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.api.ticketscloud.dto.order import Order
from fanfan.application.interactors.ticketscloud.process_tcloud_order import (
    ProcessTCloudOrder,
    ProcessTCloudOrderInput,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

webhooks_router = APIRouter(tags=["Webhooks"], prefix="/webhooks")


class TCloudWebhookPayload(BaseModel):
    data: Order
    type: str  # TODO Enforce possible types later


class TCloudWebhookResponse(BaseModel):
    new_tickets_count: int


@webhooks_router.post(
    "/tcloud/{token}",
    summary="Process TicketsCloud webhook",
    description="Handles incoming webhook events from TicketsCloud ticketing system.",
    responses={
        200: {"description": "Webhook processed successfully."},
        400: {"model": ErrorMessage, "description": "Invalid webhook payload."},
        404: {"description": "Unknown endpoint."},
    },
)
@inject
async def process_tcloud_order(
    token: str,
    data: TCloudWebhookPayload,
    config: FromDishka[TCloudConfig],
    proceed_tcloud_order: FromDishka[ProcessTCloudOrder],
) -> TCloudWebhookResponse:
    # TicketsCloud cannot sign or authenticate its webhook requests, so the only
    # gate is an unguessable token in the URL it POSTs to. Compare in constant
    # time and, when no secret is configured, fail closed. Respond 404 so the
    # endpoint is indistinguishable from a non-existent route.
    expected = config.webhook_secret
    if expected is None or not secrets.compare_digest(
        token, expected.get_secret_value()
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # TODO Don't trust the payload body. Re-fetch the order from the
    # authenticated TicketsCloud API by id and act on that, so a leaked token
    # alone cannot mint tickets.
    result = await proceed_tcloud_order(ProcessTCloudOrderInput(order=data.data))
    return TCloudWebhookResponse(new_tickets_count=result.new_tickets_count)
