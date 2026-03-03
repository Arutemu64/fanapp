from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from fanfan.application.auth.authenticate_user import (
    AuthenticateUser,
    AuthenticateUserCommand,
)
from fanfan.application.auth.change_email import (
    ChangeEmail,
    ChangeEmailCommand,
)
from fanfan.application.auth.change_password import (
    ChangePassword,
    ChangePasswordCommand,
)
from fanfan.application.auth.login_telegram import LoginTelegram, LoginTelegramCommand
from fanfan.application.auth.refresh_access_token import (
    RefreshAccessToken,
    RefreshAccessTokenCommand,
)
from fanfan.application.auth.register_user import RegisterUser, RegisterUserCommand
from fanfan.application.auth.request_email_verification import RequestEmailVerification
from fanfan.application.auth.verify_email import VerifyEmail, VerifyEmailCommand
from fanfan.core.dto.token import Token
from fanfan.core.dto.user import UserBaseDTO
from fanfan.core.exceptions.auth import (
    AuthenticationError,
    IncorrectPassword,
    InvalidToken,
    TokenExpired,
    UserNotAuthenticated,
)
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    UserAlreadyExists,
    UserNotFound,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

auth_router = APIRouter(tags=["Authentication"], prefix="/auth")


def _set_auth_cookies(response: Response, token: Token) -> None:
    response.set_cookie(
        key="access_token",
        value=token.access_token,
        httponly=True,
        max_age=1800,
        samesite="lax",
        secure=False,
    )
    response.set_cookie(
        key="refresh_token",
        value=token.refresh_token,
        httponly=True,
        max_age=604800,
        samesite="lax",
        secure=False,
    )


def _delete_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=False,
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="lax",
        secure=False,
    )


@auth_router.post(
    "/login",
    summary="Login and get access token",
    description="Authenticates user with username and password, "
    "returns JWT access and refresh tokens. "
    "Tokens are also set as HttpOnly cookies.",
    responses={
        200: {"model": Token, "description": "Successfully authenticated."},
        401: {
            "model": ErrorMessage,
            "description": "Invalid username or password.",
        },
    },
)
@inject
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    interactor: FromDishka[AuthenticateUser],
    response: Response,
) -> Token:
    try:
        token = await interactor(
            AuthenticateUserCommand(
                login=form_data.username, password=form_data.password
            )
        )
    except (UserNotFound, AuthenticationError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    else:
        _set_auth_cookies(response, token)
        return token


@auth_router.post(
    "/refresh",
    summary="Refresh access token",
    description="Uses a refresh token cookie to issue new access and refresh tokens "
    "(token rotation). Old cookies are replaced.",
    responses={
        200: {"model": Token, "description": "Tokens refreshed successfully."},
        401: {
            "model": ErrorMessage,
            "description": "Refresh token is missing, invalid, or expired.",
        },
    },
)
@inject
async def refresh_access_token(
    request: Request,
    response: Response,
    interactor: FromDishka[RefreshAccessToken],
) -> Token:
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        token = await interactor(RefreshAccessTokenCommand(refresh_token=refresh_token))
    except InvalidToken as e:
        raise HTTPException(status_code=401, detail="Invalid token type") from e
    else:
        _set_auth_cookies(response, token)
        return token


@auth_router.post(
    "/register",
    status_code=201,
    summary="Register a new user",
    description="Creates a new user account with an email and password. "
    "A username is generated automatically.",
    responses={
        201: {
            "model": UserBaseDTO,
            "description": "User successfully registered.",
        },
        409: {
            "model": ErrorMessage,
            "description": "Conflict: username or email already in use.",
        },
    },
)
@inject
async def register_user(
    data: RegisterUserCommand,
    interactor: FromDishka[RegisterUser],
) -> UserBaseDTO:
    try:
        result = await interactor(data)
    except UserAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    return result


@auth_router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change user password",
    description="Changes the authenticated user's password. "
    "Requires the current password for verification.",
    responses={
        200: {"description": "Password changed successfully."},
        409: {
            "model": ErrorMessage,
            "description": "Current password is incorrect.",
        },
    },
)
@inject
async def change_password(
    data: ChangePasswordCommand,
    interactor: FromDishka[ChangePassword],
) -> None:
    try:
        result = await interactor(data)
    except IncorrectPassword as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    return result


@auth_router.post(
    "/change-email",
    status_code=status.HTTP_200_OK,
    summary="Change user email",
    description="Changes the current user's email address "
    "and sends a verification link to the new email.",
    responses={
        200: {"description": "Email changed and verification requested."},
        404: {"model": ErrorMessage, "description": "User not found."},
        409: {
            "model": ErrorMessage,
            "description": "Email already in use by another account.",
        },
    },
)
@inject
async def change_email(
    data: ChangeEmailCommand,
    interactor: FromDishka[ChangeEmail],
) -> None:
    try:
        await interactor(data)
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
    except EmailAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@auth_router.post(
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


@auth_router.post(
    "/verify-email",
    summary="Verify user email",
    description="Verifies a user's email address using a signed token "
    "received via email.",
    responses={
        200: {"description": "Email successfully verified."},
        400: {
            "model": ErrorMessage,
            "description": "Token is invalid or expired.",
        },
        404: {"model": ErrorMessage, "description": "User not found."},
    },
)
@inject
async def verify_email(
    data: VerifyEmailCommand,
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


@auth_router.post(
    "/logout",
    summary="Logout user",
    description="Clears authentication cookies to log out the current user.",
    responses={
        200: {"description": "Successfully logged out."},
    },
)
@inject
async def logout_user(response: Response) -> None:
    _delete_auth_cookies(response)
    return


@auth_router.post("/login_telegram")
@inject
async def login_with_telegram(
    response: Response,
    data: LoginTelegramCommand,
    interactor: FromDishka[LoginTelegram],
) -> Token:
    token = await interactor(data)
    _set_auth_cookies(response, token)
    return token
