import logging
import secrets
import time

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.application.interactors.festengine.handle_festengine_event import (
    FestEngineEventInput,
    FestEngineEventOutput,
    HandleFestEngineEvent,
)
from fanfan.application.interactors.tickets.process_ticket_order import (
    ProcessTicketOrder,
    ProcessTicketOrderInput,
)
from fanfan.presentation.web.festengine import (
    FestEngineConfig,
    SignedRequest,
    verify_signature,
)
from fanfan.presentation.web.schemas.error import ProblemDetails

logger = logging.getLogger(__name__)

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


@webhooks_router.post(
    "/festengine",
    summary="Process FestEngine webhook",
    description=(
        "Turns FestEngine stage events into schedule edits: set current, skip, "
        "move. Signed per Standard Webhooks; see docs/backend.md "
        '"FestEngine webhooks" for the contract.'
    ),
    responses={
        200: {"description": "Event handled, ignored or stale."},
        400: {"model": ProblemDetails, "description": "A schedule rule refused it."},
        403: {"model": ProblemDetails, "description": "System user lacks rights."},
        404: {"description": "Unknown endpoint or unknown act number."},
        429: {"model": ProblemDetails, "description": "Announcement cooldown."},
    },
)
@inject
async def process_festengine_event(
    request: Request,
    config: FromDishka[FestEngineConfig],
    handle_event: FromDishka[HandleFestEngineEvent],
) -> FestEngineEventOutput:
    secret = config.webhook_secret
    if secret is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # The signature covers the exact bytes, so read them before parsing.
    signed = SignedRequest(
        msg_id=request.headers.get("webhook-id"),
        timestamp=request.headers.get("webhook-timestamp"),
        signatures=request.headers.get("webhook-signature"),
        body=await request.body(),
    )
    if not verify_signature(secret.get_secret_value(), signed, now=time.time()):
        logger.warning("FestEngine webhook signature rejected")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        event = FestEngineEventInput.model_validate_json(signed.body)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc
    return await handle_event(event)
