import datetime

from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from fanfan.adapters.auth.utils.jwt import (
    ACCESS_TOKEN_TTL,
    REFRESH_TOKEN_TTL,
    JwtTokenProcessor,
)
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
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
from fanfan.core.dto.user import UserBaseDTO
from fanfan.core.exceptions.auth import (
    AuthenticationError,
    IncorrectPassword,
    InvalidToken,
    RefreshTokenReused,
    TokenExpired,
    UserNotAuthenticated,
)
from fanfan.core.exceptions.users import (
    EmailAlreadyExists,
    UserAlreadyExists,
    UserNotFound,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.schemas.error import ErrorMessage

auth_router = APIRouter(tags=["Authentication"], prefix="/auth")

# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------
# Derive max_age from JWT TTL constants so they never drift out of sync.
ACCESS_TOKEN_MAX_AGE = int(ACCESS_TOKEN_TTL.total_seconds())  # 900s (15 min)
REFRESH_TOKEN_MAX_AGE = int(REFRESH_TOKEN_TTL.total_seconds())  # 604800s (7 days)


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str, config: WebConfig
) -> None:
    """Write auth tokens into HttpOnly cookies on the response.

    Both cookies use path="/" because the SvelteKit SSR server needs access
    to refresh_token to perform server-side token refresh on behalf of the
    browser (the browser must send it to SvelteKit, not just to /auth/ paths).
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_MAX_AGE,
        samesite="lax",
        secure=config.cookie_secure,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=REFRESH_TOKEN_MAX_AGE,
        samesite="lax",
        secure=config.cookie_secure,
        path="/",
    )


def _delete_auth_cookies(response: Response, config: WebConfig) -> None:
    """Clear auth cookies. Path must match what was set, otherwise cookie stays."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@auth_router.post(
    "/login",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Login and get access token",
    description="Authenticates user with username and password. "
    "Sets HttpOnly cookies with JWT access and refresh tokens.",
    responses={
        204: {"description": "Successfully authenticated. Tokens set in cookies."},
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
    config: FromDishka[WebConfig],
    response: Response,
) -> None:
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

    # Tokens go into HttpOnly cookies only — not in the response body.
    _set_auth_cookies(response, token.access_token, token.refresh_token, config)


@auth_router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Refresh access token",
    description="Uses the refresh_token cookie to issue fresh access and refresh tokens "
    "(token rotation). Old cookies are replaced.",
    responses={
        204: {"description": "Tokens refreshed successfully. New cookies set."},
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
    config: FromDishka[WebConfig],
) -> None:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        token = await interactor(RefreshAccessTokenCommand(refresh_token=refresh_token))
    except (InvalidToken, RefreshTokenReused, AuthenticationError) as e:
        raise HTTPException(status_code=401, detail=e.message) from e

    _set_auth_cookies(response, token.access_token, token.refresh_token, config)


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
) -> None:
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
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="Clears auth cookies and invalidates the refresh token "
    "so it can't be replayed even if stolen.",
    responses={
        204: {"description": "Successfully logged out."},
    },
)
@inject
async def logout_user(
    request: Request,
    response: Response,
    jwt: FromDishka[JwtTokenProcessor],
    token_registry: FromDishka[RedisAuthTokenRegistry],
    config: FromDishka[WebConfig],
) -> None:
    # Server-side invalidation: mark the refresh token JTI as consumed in Redis
    # so it can't be replayed even if someone intercepted the cookie.
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = jwt.validate_token(refresh_token, expected_type="refresh_token")
            now_ts = int(datetime.datetime.now(datetime.UTC).timestamp())
            ttl_seconds = max(payload.exp - now_ts, 1)
            await token_registry.revoke_refresh_token_jti(
                jti=payload.jti, ttl_seconds=ttl_seconds
            )
        except Exception:
            pass  # Token may already be expired/invalid — that's fine, just clear cookies

    _delete_auth_cookies(response, config)


@auth_router.post("/login_telegram")
@inject
async def login_with_telegram(
    response: Response,
    data: LoginTelegramCommand,
    interactor: FromDishka[LoginTelegram],
    config: FromDishka[WebConfig],
) -> None:
    token = await interactor(data)
    _set_auth_cookies(response, token.access_token, token.refresh_token, config)
