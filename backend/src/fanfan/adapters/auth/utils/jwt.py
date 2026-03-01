import datetime
from dataclasses import dataclass
from datetime import timedelta

import jwt
from adaptix import Retort
from jwt import InvalidTokenError

from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig

TOKEN_TTL = datetime.timedelta(minutes=15)
ALGORITHM = "HS256"


@dataclass(slots=True, frozen=True)
class JwtTokenData:
    sub: UserId
    token_type: str
    exp: timedelta


class JwtTokenProcessor:
    def __init__(self, config: WebConfig):
        self.config = config
        self.retort = Retort()

    def create_access_token(self, user_id: UserId) -> str:
        payload = {
            "sub": str(user_id),
            "type": "access_token",
            "exp": datetime.datetime.now(datetime.UTC) + timedelta(minutes=15),
        }
        return jwt.encode(payload, self.config.secret_key.get_secret_value(), ALGORITHM)

    def create_refresh_token(self, user_id: UserId) -> str:
        payload = {
            "sub": str(user_id),
            "type": "refresh_token",
            "exp": datetime.datetime.now(datetime.UTC) + timedelta(days=7),
        }
        return jwt.encode(payload, self.config.secret_key.get_secret_value(), ALGORITHM)

    def validate_token(self, token: str) -> JwtTokenData:
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key.get_secret_value(),
                ALGORITHM,
            )
        except InvalidTokenError as e:
            raise AuthenticationError from e

        try:
            return JwtTokenData(
                sub=UserId(int(payload["sub"])),
                token_type=payload["type"],
                exp=payload["exp"],
            )
        except ValueError as e:
            raise AuthenticationError from e
