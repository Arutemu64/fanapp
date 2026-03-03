from pwdlib import PasswordHash

from fanfan.adapters.auth.utils.jwt import JwtTokenProcessor
from fanfan.core.dto.token import Token
from fanfan.core.vo.user import UserId


class SecurityService:
    def __init__(self, jwt: JwtTokenProcessor):
        self.jwt = jwt
        self.password_hash = PasswordHash.recommended()

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        return self.password_hash.verify(password, hashed_password)

    def create_token(self, user_id: UserId) -> Token:
        access_token = self.jwt.create_access_token(user_id=user_id)
        refresh_token = self.jwt.create_refresh_token(user_id=user_id)
        return Token(
            access_token=access_token, refresh_token=refresh_token, token_type="Bearer"
        )
