from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import JSONResponse

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


@webhooks_router.post(
    "/tcloud",
    summary="Process TicketsCloud webhook",
    description="Handles incoming webhook events from TicketsCloud ticketing system.",
    responses={
        200: {"description": "Webhook processed successfully."},
        400: {"model": ErrorMessage, "description": "Invalid webhook payload."},
    },
)
@inject
async def process_tcloud_order(
    data: TCloudWebhookPayload,
    proceed_tcloud_order: FromDishka[ProcessTCloudOrder],
) -> JSONResponse:
    result = await proceed_tcloud_order(ProcessTCloudOrderInput(order=data.data))
    data = {"new_tickets_count": result.new_tickets_count}
    return JSONResponse(content=data, status_code=200)
