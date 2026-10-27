import enum
import secrets
from datetime import UTC, datetime

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.application.interactors.schedule_mgmt.apply_stage_console_action import (
    ApplyStageConsoleAction,
)
from fanfan.application.interactors.tickets.process_ticket_order import (
    ProcessTicketOrder,
    ProcessTicketOrderInput,
)
from fanfan.presentation.web.festengine.config import FestEngineConfig
from fanfan.presentation.web.festengine.events import FestEngineEvent, to_action_input
from fanfan.presentation.web.festengine.signature import verify_signature
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


class FestEngineWebhookStatus(enum.StrEnum):
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    IGNORED = "ignored"
    STALE = "stale"


class FestEngineWebhookResponse(BaseModel):
    status: FestEngineWebhookStatus


@webhooks_router.post(
    "/festengine",
    summary="Process FestEngine webhook",
    description=(
        "Applies stage events from the FestEngine playback console: the current "
        "act, skips and moves. Signed per Standard Webhooks."
    ),
    responses={
        200: {"description": "Event applied, already applied, or ignored."},
        400: {"model": ProblemDetails, "description": "The edit breaks a rule."},
        404: {
            "model": ProblemDetails,
            "description": "Unknown endpoint, bad signature, or unknown number.",
        },
        422: {"model": ProblemDetails, "description": "Malformed payload."},
        429: {"model": ProblemDetails, "description": "Announcement cooldown."},
    },
)
@inject
async def process_festengine_event(
    request: Request,
    config: FromDishka[FestEngineConfig],
    apply_action: FromDishka[ApplyStageConsoleAction],
) -> FestEngineWebhookResponse:
    secret = config.webhook_secret
    # The signed bytes must be the raw body, so it is read before parsing.
    body = await request.body()
    now = datetime.now(UTC)
    if secret is None or not verify_signature(
        secret.get_secret_value(),
        msg_id=request.headers.get("webhook-id"),
        timestamp=request.headers.get("webhook-timestamp"),
        signature_header=request.headers.get("webhook-signature"),
        body=body,
        now=now,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        event = FestEngineEvent.model_validate_json(body)
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    if event.is_stale(now):
        return FestEngineWebhookResponse(status=FestEngineWebhookStatus.STALE)
    action_input = to_action_input(event)
    if action_input is None:
        return FestEngineWebhookResponse(status=FestEngineWebhookStatus.IGNORED)
    changed = await apply_action(action_input)
    if changed:
        return FestEngineWebhookResponse(status=FestEngineWebhookStatus.UPDATED)
    return FestEngineWebhookResponse(status=FestEngineWebhookStatus.UNCHANGED)
