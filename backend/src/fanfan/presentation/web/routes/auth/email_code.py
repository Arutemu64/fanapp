from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.auth.confirm_email_code import (
    ConfirmEmailCode,
    ConfirmEmailCodeInput,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

email_code_router = APIRouter()


@email_code_router.post(
    "/confirm-email-code",
    summary="Confirm user email with code",
    description="Confirms the new email address using a one-time code received at that address.",  # noqa: E501
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
