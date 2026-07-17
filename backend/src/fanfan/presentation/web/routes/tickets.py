from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.tickets.generate_tickets import (
    GenerateTickets,
    GenerateTicketsInput,
    GenerateTicketsOutput,
)
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.security import session_security

tickets_router = APIRouter(
    tags=["Tickets"],
    prefix="/tickets",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@tickets_router.post(
    "/generate",
    summary="Generate tickets",
    description=(
        "Generates a batch of new tickets for the given role. Requires the "
        "'tickets:generate' permission. Returns the created barcodes."
    ),
    responses={
        200: {
            "model": GenerateTicketsOutput,
            "description": "Tickets generated successfully.",
        },
        409: {
            "model": ErrorMessage,
            "description": "A generated barcode collided; retry the request.",
        },
    },
)
@inject
async def generate_tickets(
    data: GenerateTicketsInput,
    interactor: FromDishka[GenerateTickets],
) -> GenerateTicketsOutput:
    return await interactor(data)
