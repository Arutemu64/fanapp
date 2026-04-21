from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.interactors.tickets.link_ticket import (
    LinkTicket,
    LinkTicketInput,
)
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.tickets import (
    TicketAlreadyUsed,
    TicketNotFound,
    UserAlreadyHasTicketLinked,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

tickets_router = APIRouter()


@tickets_router.post(
    "/ticket",
    summary="Link ticket",
    description="Links provided ticket to current user.",
    responses={
        200: {"description": "Ticket linked successfully."},
        404: {"model": ErrorMessage, "description": "Ticket not found."},
        409: {
            "model": ErrorMessage,
            "description": "User already has a ticket linked or ticket is already used.",
        },
    },
)
@inject
async def link_ticket(
    data: LinkTicketInput,
    interactor: FromDishka[LinkTicket],
) -> None:
    try:
        return await interactor(data)
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
        ) from e
    except TicketNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
    except TicketAlreadyUsed as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=e.message
        ) from e
    except UserAlreadyHasTicketLinked as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=e.message
        ) from e
