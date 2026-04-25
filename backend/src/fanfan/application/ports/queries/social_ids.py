from typing import Protocol

from fanfan.application.dto.user import UserSocialAccountDTO
from fanfan.core.vo.user import UserId


class SocialIdentityQuery(Protocol):
    async def read_user_social_accounts(
        self,
        user_id: UserId,
    ) -> list[UserSocialAccountDTO]: ...
