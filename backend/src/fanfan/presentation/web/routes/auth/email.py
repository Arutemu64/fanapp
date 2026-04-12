from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.interactors.auth.request_email_verification import (
    RequestEmailVerification,
)
from fanfan.application.interactors.auth.verify_email import (
    VerifyEmail,
    VerifyEmailInput,
)
from fanfan.core.exceptions.auth import InvalidToken, TokenExpired, UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound
from fanfan.presentation.web.schemas.error import ErrorMessage

email_router = APIRouter()


@email_router.post(
    "/request-email-verification",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a new email verification link",
    description="Sends a new verification email to the current user's email address.",
    responses={
        202: {"description": "Verification email sent."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def request_email_verification(
    interactor: FromDishka[RequestEmailVerification],
) -> None:
    try:
        await interactor()
    except UserNotAuthenticated as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@email_router.post(
    "/verify-email",
    summary="Verify user email",
    description="Verifies a user's email address using a signed token "
    "received via email.",
    responses={
        200: {"description": "Email successfully verified."},
        400: {"model": ErrorMessage, "description": "Token is invalid or expired."},
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def verify_email(
    data: VerifyEmailInput,
    interactor: FromDishka[VerifyEmail],
) -> None:
    try:
        await interactor(data)
    except (InvalidToken, TokenExpired) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except UserNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
