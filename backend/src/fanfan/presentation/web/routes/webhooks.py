import secrets

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.application.interactors.tickets.process_ticket_order import (
    ProcessTicketOrder,
    ProcessTicketOrderInput,
)
from fanfan.presentation.web.schemas.error import ProblemDetails

webhooks_router = APIRouter(tags=["Webhooks"], prefix="/webhooks")


class TCloudWebhookOrderRef(BaseModel):
    id: str


class TCloudWebhookPayload(BaseModel):
    data: TCloudWebhookOrderRef


class TCloudWebhookResponse(BaseModel):
    new_tickets_count: int


@webhooks_router.post(
    "/tcloud/{token}",
    summary="Process TicketsCloud webhook",
    description="Handles incoming webhook events from TicketsCloud ticketing system.",
    responses={
        200: {"description": "Webhook processed successfully."},
        400: {"model": ProblemDetails, "description": "Invalid webhook payload."},
        404: {"description": "Unknown endpoint."},
    },
)
@inject
async def process_tcloud_order(
    token: str,
    data: TCloudWebhookPayload,
    config: FromDishka[TCloudConfig],
    proceed_tcloud_order: FromDishka[ProcessTicketOrder],
) -> TCloudWebhookResponse:
    expected = config.webhook_secret
    if expected is None or not secrets.compare_digest(
        token, expected.get_secret_value()
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    result = await proceed_tcloud_order(ProcessTicketOrderInput(order_id=data.data.id))
    return TCloudWebhookResponse(new_tickets_count=result.new_tickets_count)
