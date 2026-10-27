from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query

from fanfan.application.dto.page import CursorPagination
from fanfan.application.dto.ticket import TicketListFilter
from fanfan.application.interactors.tickets.generate_tickets import (
    GenerateTickets,
    GenerateTicketsInput,
    GenerateTicketsOutput,
)
from fanfan.application.interactors.tickets.list_tickets import (
    ListTickets,
    ListTicketsInput,
    ListTicketsOutput,
)
from fanfan.application.interactors.tickets.tcloud_event_roles import (
    GetTCloudEventRoles,
    SetTCloudEventRoles,
    SetTCloudEventRolesInput,
    TCloudEventRolesOutput,
)
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ProblemDetails
from fanfan.presentation.web.schemas.tickets import TicketListQuery
from fanfan.presentation.web.security import session_security

tickets_router = APIRouter(
    tags=["Tickets"],
    prefix="/tickets",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)
ticket_batches_router = APIRouter(
    tags=["Tickets"],
    prefix="/ticket-batches",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@tickets_router.get(
    "",
    summary="List tickets",
    description=(
        "Newest-first list of every ticket, generated or imported from "
        "TicketsCloud, with the user who linked it. Search matches a "
        "case-insensitive substring of the ticket number. Requires "
        "'tickets:manage'."
    ),
    responses={
        200: {"description": "Tickets retrieved successfully."},
    },
)
@inject
async def list_tickets(
    interactor: FromDishka[ListTickets],
    query: Annotated[TicketListQuery, Query()],
) -> ListTicketsOutput:
    data = ListTicketsInput(
        pagination=CursorPagination.from_token(limit=query.limit, cursor=query.cursor),
        ticket_filter=TicketListFilter(search=query.q),
    )
    return await interactor(data)


@tickets_router.get(
    "/tcloud-event-roles",
    summary="Get TicketsCloud event roles",
    description=(
        "Returns which role a ticket bought for each TicketsCloud event grants, "
        "and whether TicketsCloud is configured for this deployment. An event "
        "left out grants the visitor role. Requires 'tickets:manage'."
    ),
    responses={
        200: {"description": "Event roles retrieved successfully."},
    },
)
@inject
async def get_tcloud_event_roles(
    interactor: FromDishka[GetTCloudEventRoles],
) -> TCloudEventRolesOutput:
    return await interactor()


@tickets_router.put(
    "/tcloud-event-roles",
    status_code=204,
    summary="Replace TicketsCloud event roles",
    description=(
        "Replaces the whole event-to-role mapping. Applies to tickets imported "
        "from now on; stored tickets keep their role. Requires 'tickets:manage'."
    ),
    responses={
        204: {"description": "Event roles saved."},
    },
)
@inject
async def set_tcloud_event_roles(
    data: SetTCloudEventRolesInput,
    interactor: FromDishka[SetTCloudEventRoles],
) -> None:
    await interactor(data)


@ticket_batches_router.post(
    "",
    status_code=201,
    summary="Generate a batch of tickets",
    description=(
        "Generates a batch of new tickets for the given role. Requires the "
        "'tickets:manage' permission. Returns the created barcodes. The client "
        "supplies the batch ID, so repeating the same request returns the "
        "existing batch instead of generating another."
    ),
    responses={
        201: {"description": "Tickets generated, or an identical batch replayed."},
        409: {
            "model": ProblemDetails,
            "description": "The batch ID belongs to a different batch.",
        },
    },
)
@inject
async def create_ticket_batch(
    data: GenerateTicketsInput,
    interactor: FromDishka[GenerateTickets],
) -> GenerateTicketsOutput:
    return await interactor(data)
