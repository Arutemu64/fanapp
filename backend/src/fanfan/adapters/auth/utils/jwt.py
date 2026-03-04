import datetime
import uuid
from dataclasses import dataclass

import jwt
from jwt import InvalidTokenError

from fanfan.core.exceptions.auth import AuthenticationError, InvalidToken
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig

ACCESS_TOKEN_TTL = datetime.timedelta(minutes=15)
REFRESH_TOKEN_TTL = datetime.timedelta(days=7)
ALGORITHM = "HS256"


@dataclass(slots=True, frozen=True)
class JwtTokenData:
    sub: UserId
    token_type: str
    exp: int
    jti: str
    iat: int
    nbf: int
    iss: str
    aud: str


class JwtTokenProcessor:
    def __init__(self, config: WebConfig):
        self.config = config

    def _base_payload(
        self,
        user_id: UserId,
        token_type: str,
        ttl: datetime.timedelta,
    ) -> dict[str, object]:
        now = datetime.datetime.now(datetime.UTC)
        return {
            "sub": str(user_id),
            "type": token_type,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "nbf": now,
            "exp": now + ttl,
            "iss": self.config.jwt_issuer,
            "aud": self.config.jwt_audience,
        }

    def create_access_token(self, user_id: UserId) -> str:
        payload = self._base_payload(
            user_id=user_id,
            token_type="access_token",  # noqa: S106
            ttl=ACCESS_TOKEN_TTL,
        )
        return jwt.encode(payload, self.config.secret_key.get_secret_value(), ALGORITHM)

    def create_refresh_token(self, user_id: UserId) -> str:
        payload = self._base_payload(
            user_id=user_id,
            token_type="refresh_token",  # noqa: S106
            ttl=REFRESH_TOKEN_TTL,
        )
        return jwt.encode(payload, self.config.secret_key.get_secret_value(), ALGORITHM)

    def validate_token(
        self,
        token: str,
        expected_type: str | None = None,
    ) -> JwtTokenData:
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key.get_secret_value(),
                algorithms=[ALGORITHM],
                audience=self.config.jwt_audience,
                issuer=self.config.jwt_issuer,
                options={
                    "require": [
                        "sub",
                        "type",
                        "jti",
                        "iat",
                        "nbf",
                        "exp",
                        "iss",
                        "aud",
                    ]
                },
            )
        except InvalidTokenError as e:
            raise AuthenticationError from e

        try:
            token_data = JwtTokenData(
                sub=UserId(payload["sub"]),
                token_type=str(payload["type"]),
                exp=int(payload["exp"]),
                jti=str(payload["jti"]),
                iat=int(payload["iat"]),
                nbf=int(payload["nbf"]),
                iss=str(payload["iss"]),
                aud=str(payload["aud"]),
            )
        except (KeyError, TypeError, ValueError) as e:
            raise AuthenticationError from e

        if expected_type is not None and token_data.token_type != expected_type:
            raise InvalidToken

        return token_data
