from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from starlette import status

from fanfan.application.interactors.auth.confirm_email_code import (
    ConfirmEmailCode,
    ConfirmEmailCodeInput,
)
from fanfan.application.interactors.auth.request_email_code import RequestEmailCode
from fanfan.presentation.web.schemas.error import ErrorMessage

email_code_router = APIRouter()


@email_code_router.post(
    "/request-email-code",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a new email confirmation code",
    description="Sends a new confirmation code to the current user's email address.",
    responses={
        202: {"description": "Confirmation code sent."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def request_email_code(
    interactor: FromDishka[RequestEmailCode],
) -> None:
    await interactor()


@email_code_router.post(
    "/confirm-email-code",
    summary="Confirm user email with code",
    description="Confirms the current user's email address using a one-time code "
    "received via email.",
    responses={
        200: {"description": "Email successfully confirmed."},
        400: {"model": ErrorMessage, "description": "Code is invalid or expired."},
        401: {"model": ErrorMessage, "description": "User not authenticated."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def confirm_email_code(
    data: ConfirmEmailCodeInput,
    interactor: FromDishka[ConfirmEmailCode],
) -> None:
    await interactor(data)
