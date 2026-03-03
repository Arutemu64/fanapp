from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from starlette import status

from fanfan.adapters.auth.utils.jwt import JwtTokenProcessor
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import AuthenticationError
from fanfan.core.vo.user import UserId


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        # 1. Check Header (Standard OAuth2)
        authorization = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)

        # 2. Check Cookie (Web/Browser)
        if not authorization or scheme.lower() != "bearer":
            # If header is missing or malformed, fallback to cookie
            param = request.cookies.get("access_token")

        # 3. Validation
        if not param:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )
            return None

        return param


class WebIdProvider(IdProvider):
    def __init__(
        self,
        request: Request,
        jwt: JwtTokenProcessor,
        oauth2: OAuth2PasswordBearerWithCookie,
    ):
        self.request = request
        self.jwt = jwt
        self.oauth2 = oauth2

    async def get_current_user_id(self) -> UserId | None:
        token = await self.oauth2(self.request)
        if token is None:
            return None
        try:
            jwt_data = self.jwt.validate_token(token, expected_type="access_token")
        except AuthenticationError:
            return None
        else:
            return UserId(jwt_data.sub)
