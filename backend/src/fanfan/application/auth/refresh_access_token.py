from pydantic import BaseModel

from fanfan.adapters.auth.utils.jwt import JwtTokenProcessor
from fanfan.core.dto.token import Token
from fanfan.core.exceptions.auth import InvalidToken


class RefreshAccessTokenCommand(BaseModel):
    refresh_token: str


class RefreshAccessToken:
    def __init__(self, jwt: JwtTokenProcessor):
        self.jwt = jwt

    async def __call__(self, data: RefreshAccessTokenCommand) -> Token:
        payload = self.jwt.validate_token(data.refresh_token)
        if payload.token_type != "refresh_token":
            raise InvalidToken

        user_id = payload.sub
        new_access_token = self.jwt.create_access_token(user_id=user_id)
        new_refresh_token = self.jwt.create_refresh_token(user_id=user_id)

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
        )
