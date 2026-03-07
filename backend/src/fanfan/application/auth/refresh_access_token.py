import datetime

from pydantic import BaseModel

from fanfan.adapters.auth.utils.jwt import JwtTokenProcessor
from fanfan.adapters.redis.auth_token_registry import RedisAuthTokenRegistry
from fanfan.core.dto.token import Token
from fanfan.core.exceptions.auth import RefreshTokenReused


class RefreshAccessTokenCommand(BaseModel):
    refresh_token: str


class RefreshAccessToken:
    def __init__(self, jwt: JwtTokenProcessor, token_registry: RedisAuthTokenRegistry):
        self.jwt = jwt
        self.token_registry = token_registry

    async def __call__(self, data: RefreshAccessTokenCommand) -> Token:
        payload = self.jwt.validate_token(
            data.refresh_token,
            expected_type="refresh_token",
        )

        now_ts = int(datetime.datetime.now(datetime.UTC).timestamp())
        ttl_seconds = max(payload.exp - now_ts, 1)
        is_fresh = await self.token_registry.consume_refresh_token_jti(
            jti=payload.jti,
            ttl_seconds=ttl_seconds,
        )
        if not is_fresh:
            raise RefreshTokenReused

        user_id = payload.sub
        new_access_token = self.jwt.create_access_token(user_id=user_id)
        new_refresh_token = self.jwt.create_refresh_token(user_id=user_id)

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",  # noqa: S106
        )
