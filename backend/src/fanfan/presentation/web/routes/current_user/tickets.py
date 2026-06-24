from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.tickets.link_ticket import (
    LinkTicket,
    LinkTicketInput,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

tickets_router = APIRouter()


@tickets_router.post(
    "/ticket",
    status_code=204,
    summary="Link ticket",
    description="Links provided ticket to current user.",
    responses={
        204: {"description": "Ticket linked successfully."},
        404: {"model": ErrorMessage, "description": "Ticket not found."},
        409: {
            "model": ErrorMessage,
            "description": (
                "User already has a ticket linked or ticket is already used."
            ),
        },
    },
)
@inject
async def link_ticket(
    data: LinkTicketInput,
    interactor: FromDishka[LinkTicket],
) -> None:
    await interactor(data)
