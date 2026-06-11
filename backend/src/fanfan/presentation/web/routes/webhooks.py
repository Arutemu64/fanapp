import secrets

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.application.interactors.ticketscloud.process_tcloud_order import (
    ProcessTCloudOrder,
    ProcessTCloudOrderInput,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

webhooks_router = APIRouter(tags=["Webhooks"], prefix="/webhooks")


class TCloudWebhookOrderRef(BaseModel):
    # The webhook body is untrusted, so we read only the order id from it and
    # re-fetch the authoritative order from the API. Other fields are ignored.
    id: str


class TCloudWebhookPayload(BaseModel):
    data: TCloudWebhookOrderRef
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

    # Only the order id is trusted; the interactor re-fetches the order from the
    # authenticated API, so a leaked token alone cannot mint tickets.
    result = await proceed_tcloud_order(ProcessTCloudOrderInput(order_id=data.data.id))
    return TCloudWebhookResponse(new_tickets_count=result.new_tickets_count)
