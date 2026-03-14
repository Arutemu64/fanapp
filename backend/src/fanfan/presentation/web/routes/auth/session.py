import datetime

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request, Response
from redis.exceptions import RedisError
from starlette import status

from fanfan.adapters.auth.utils.jwt import JwtTokenProcessor
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
from fanfan.application.auth.refresh_access_token import (
    RefreshAccessToken,
    RefreshAccessTokenCommand,
)
from fanfan.core.exceptions.auth import (
    AuthenticationError,
    InvalidToken,
    RefreshTokenReused,
    TokenExpired,
)
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.routes.auth.cookies import (
    delete_auth_cookies,
    set_auth_cookies,
)
from fanfan.presentation.web.schemas.error import ErrorMessage

session_router = APIRouter()


@session_router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Refresh access token",
    description="Uses the refresh_token cookie to issue fresh access and refresh "
    "tokens (token rotation). Old cookies are replaced.",
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

    set_auth_cookies(response, token.access_token, token.refresh_token, config)


@session_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user",
    description="Clears auth cookies and invalidates the refresh token "
    "so it can't be replayed even if stolen.",
    responses={204: {"description": "Successfully logged out."}},
)
@inject
async def logout_user(
    request: Request,
    response: Response,
    jwt: FromDishka[JwtTokenProcessor],
    token_registry: FromDishka[RedisAuthTokenRegistry],
    config: FromDishka[WebConfig],
) -> None:
    # Best-effort token revocation before clearing cookies.
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = jwt.validate_token(refresh_token, expected_type="refresh_token")
            now_ts = int(datetime.datetime.now(datetime.UTC).timestamp())
            ttl_seconds = max(payload.exp - now_ts, 1)
            await token_registry.revoke_refresh_token_jti(
                jti=payload.jti, ttl_seconds=ttl_seconds
            )
        except (InvalidToken, TokenExpired, RedisError):
            pass

    # config is intentionally kept in the signature for DI consistency.
    _ = config
    delete_auth_cookies(response)
